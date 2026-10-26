# 04 - Build & Configuration Audit (platformio.ini, sdkconfig, partitions, CMake, provisioning)

## Summary
- **Secure Boot v2 and Flash Encryption are NOT enabled by any file in the repo.** `firmware/sdkconfig.defaults` contains zero `CONFIG_SECURE_BOOT*`, `CONFIG_SECURE_FLASH_ENC*` or `CONFIG_NVS_ENCRYPTION` symbols, while `firmware/README.md:41-43` and `firmware/SECURITY_SPECIFICATION.md:121-126` claim them. The one security-looking line (`sdkconfig.defaults:15`) is almost certainly a non-existent symbol and is silently dropped. [VERIFIED absence, INFERRED impact]
- **No octal PSRAM configuration exists** (zero `CONFIG_SPIRAM*`), despite `platformio.ini:3,16` and `README` claims of 8 MB octal PSRAM. The `esp32-s3-devkitc-1` board id does not match the N16R8 module. [VERIFIED]
- **The PlatformIO build path probably does not apply `sdkconfig.defaults` at all.** `custom_sdkconfig_defaults` (`platformio.ini:35`) is not a documented PlatformIO option; the documented mechanism is `board_build.cmake_extra_args -DSDKCONFIG_DEFAULTS=...`. Two build paths (`pio run` and `idf.py`) are therefore likely to produce different firmware. [VERIFIED docs, UNVERIFIED runtime]
- **Partition map is arithmetically clean** (no overlaps, all offsets on 0x1000, app slots on 0x10000). Allocated partition entries total **12,886,016 B (0xC4A000)**; **3,837,952 B (0x3A9000) is unallocated**; 53,248 B is reserved for bootloader + partition table. [VERIFIED]
- **No CI, no lockfile, no pinned ESP-IDF or PlatformIO platform version, hard-coded version string** (`main.c:91`). No eFuse/signing/provisioning script exists anywhere in the repo. Anti-rollback is set in config with no burn procedure behind it. [VERIFIED absence]

## Scope & Method
**Files read (all read-only):** `firmware/platformio.ini`, `firmware/sdkconfig.defaults`, `firmware/partitions.csv`, `firmware/CMakeLists.txt`, `firmware/main/CMakeLists.txt`, `firmware/README.md`, `firmware/SECURITY_SPECIFICATION.md`, `firmware/main/*.c|*.h` (all 8 `.c` and 8 `.h`), `PROJECT.md`, `README.md`, `sim/README.md`, `sim/run_renode.sh`, `sim/renode/automoto.resc`, `sim/renode/automoto.repl`, `sim/wokwi/diagram.json`, `docs/TARGET_MARKET_AND_USE_CASES.md` (scanned), `.gitignore`, and a repo-wide search for `.github`, `*.yml`, `*.lock`, `*.pem`, `*.key`, `*.crt`, `espefuse`, `espsecure`, `esptool`, `idf.py`.

**External reference (only one):** PlatformIO Espressif 32 docs, `https://docs.platformio.org/en/latest/platforms/espressif32.html` (sdkconfig section, PSRAM section, Debug Level section, board table, "Stable and upstream versions"), and `https://docs.platformio.org/en/latest/frameworks/espidf.html` (Secure Boot example: `CONFIG_SECURE_BOOT=y`, `CONFIG_SECURE_BOOT_V2_ENABLED=y`).

**Could NOT verify (no toolchain, no network downloads permitted):**
- ESP-IDF Kconfig contents. Every symbol-existence statement below is from memory of ESP-IDF 5.x and is tagged `UNVERIFIABLE` where not confirmed against source.
- What PlatformIO actually writes into its generated CMake project, including whether `src_dir = main` is honored as the main component.
- Bootloader binary size, partition-table validity (`gen_esp32part.py` not run), and any compile/link result. **No build was run, and no build success or failure is claimed.**

**Verification legend:** `[VERIFIED]` = readable at the cited line or confirmed in the cited doc. `[INFERRED]` = stated assumption from VERIFIED facts. `[UNVERIFIED]` = external/toolchain fact; the confirmation step is given.

---

## Findings

### Evidence table E-1: `firmware/sdkconfig.defaults` line-by-line verdicts

Verdict key: **VALID** (name and value correct for IDF 5.x, per memory, confirm with the grep in the last column) · **SUSPICIOUS** (plausible but wrong effect, redundant, or misleading) · **WRONG** (probable non-existent symbol or wrong semantics) · **UNVERIFIABLE** (name plausible for IDF 5.x; cannot confirm here). Every unknown symbol is dropped silently; see F-04-08 for the detection job.

| Line | Symbol = value | Verdict | Note / evidence |
|---|---|---|---|
| 4 | `CONFIG_IDF_TARGET="esp32s3"` | SUSPICIOUS (P3) | Target is normally set by `idf.py set-target` or the PIO board. Hard-pinning it in defaults can make a target mismatch an error. Drop it. [UNVERIFIED mismatch behavior] |
| 5 | `CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y` | VALID | Matches `platformio.ini:17`. |
| 6 | `CONFIG_ESPTOOLPY_FLASHMODE_QIO=y` | VALID | Matches `platformio.ini:18` (`flash_mode = qio`). |
| 7 | `CONFIG_ESPTOOLPY_FLASHFREQ_80M=y` | VALID | Matches `platformio.ini:19` (80 MHz). |
| 8 | `CONFIG_PARTITION_TABLE_CUSTOM=y` | VALID | Needed for `partitions.csv` to be used. |
| 9 | `CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"` | VALID | Same file as `platformio.ini:21` (`board_build.partitions`). Two sources, same value, so no conflict. |
| 10 | `CONFIG_PARTITION_TABLE_OFFSET=0xC000` | VALID | Name and hex format correct. Implies 48 KB bootloader area, see F-04-15. |
| 13 | `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` | VALID | Matches the OTA self-test code at `main.c:72-86`. |
| 14 | `CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK=y` | UNVERIFIABLE | Name believed to exist in IDF 5.x. Needs a secure-version scheme and eFuse burn; neither exists in repo. See F-04-05. Confirm: `grep -rn ANTI_ROLLBACK $IDF_PATH/components/bootloader/Kconfig.projbuild`. |
| 15 | `CONFIG_SECURE_BOOT_SUPPORTS_PLAINTEXT_BOOTLOADER=y` | **WRONG** (probable non-existent) | I cannot match this name to any IDF 5.x Secure Boot option. Even if it exists, a "supports" flag does not enable Secure Boot. The real enable symbols are absent. Confirm: `grep -rn SUPPORTS_PLAINTEXT_BOOTLOADER $IDF_PATH/components`; expected zero hits. [UNVERIFIED] |
| 18 | `CONFIG_ESP_TASK_WDT_EN=y` | VALID | IDF 5.x `ESP_TASK_WDT_*` naming. |
| 19 | `CONFIG_ESP_TASK_WDT_INIT=y` | VALID | Needed so `esp_task_wdt_add` (`actuator_safety.c:23`) has a running WDT. |
| 20 | `CONFIG_ESP_TASK_WDT_TIMEOUT_S=3` | VALID | Consistent with the 20 ms actuator loop (`actuator_safety.c:28`). |
| 21 | `CONFIG_ESP_TASK_WDT_CHECK_IDLE_TASK_CPU0=y` | VALID | |
| 22 | `CONFIG_ESP_TASK_WDT_CHECK_IDLE_TASK_CPU1=y` | VALID | |
| 23 | `CONFIG_ESP_TASK_WDT_PANIC=y` | VALID | Panic resets the chip. README:38 claims this drives relays to a safe state. Config does not do that; see F-04-14. |
| 26 | `CONFIG_FREERTOS_HZ=1000` | VALID | Valid, unusual (default 100). |
| 27 | `CONFIG_FREERTOS_UNICORE=n` | VALID | Dual-core, matches the design. Default anyway. |
| 28 | `CONFIG_FREERTOS_OPTIMIZED_SCHEDULER=y` | UNVERIFIABLE | Likely valid, default is already y. No-op. |
| 31 | `CONFIG_BT_ENABLED=y` | VALID | Also keeps the RF entropy source valid for `esp_random` (`ble_keyless.c:26`) [INFERRED]. |
| 32 | `CONFIG_BT_BLE_ENABLED=y` | VALID | |
| 33 | `CONFIG_BT_NIMBLE_ENABLED=y` | VALID | Matches the NimBLE decision (`SECURITY_SPECIFICATION.md:45,149`). |
| 34 | `CONFIG_BT_BLUEDROID_ENABLED=n` | VALID | Matches `SECURITY_SPECIFICATION.md:45`. |
| 35 | `CONFIG_BT_NIMBLE_MEM_ALLOC_MODE_INTERNAL=y` | UNVERIFIABLE | Likely valid choice name. Consistent with having no PSRAM (F-04-06). |
| 36 | `CONFIG_BT_NIMBLE_MAX_CONNECTIONS=3` | VALID | |
| 37 | `CONFIG_BT_NIMBLE_MAX_BONDS=5` | VALID | Bonds go to NVS, which is not encrypted (F-04-03). |
| 38 | `CONFIG_BT_NIMBLE_SM_LEGACY=n` | VALID | Security-positive, but inert: `ble_keyless.c` has no SM/pairing code (`ble_keyless.c:1-29`). |
| 39 | `CONFIG_BT_NIMBLE_SM_SC=y` | VALID | Same caveat as line 38. |
| 42 | `CONFIG_PM_ENABLE=y` | VALID | No `esp_pm` call anywhere in `firmware/main` (grep). It adds runtime cost with no use [INFERRED]. |
| 43 | `CONFIG_ESP_SLEEP_POWER_DOWN_FLASH=y` | SUSPICIOUS | Applies to light sleep. The code uses deep sleep (`power_manager.c:51`), so this is ineffective. [UNVERIFIED symbol semantics] |
| 46 | `CONFIG_MBEDTLS_HARDWARE_AES=y` | VALID | Inert: no mbedtls include in `firmware/main` (grep). |
| 47 | `CONFIG_MBEDTLS_HARDWARE_SHA=y` | VALID | Inert, same reason. |
| 48 | `CONFIG_MBEDTLS_HARDWARE_MPI=y` | VALID | Inert, same reason. |
| 49 | `CONFIG_MBEDTLS_HARDWARE_GCM=y` | VALID | Inert, same reason. Confirm S3 support: `grep -rn MBEDTLS_HARDWARE_GCM $IDF_PATH/components/mbedtls/Kconfig*`. |
| 50 | `CONFIG_MBEDTLS_TLS_CLIENT_ONLY=n` | VALID | Default, no-op. |
| 51 | `CONFIG_MBEDTLS_CLIENT_SSL_SESSION_TICKETS=y` | VALID | Inert: no TLS client exists yet (`modem.c` is UART/AT only). |
| 54 | `CONFIG_ESP_TIMER_PROFILING=y` | SUSPICIOUS | Comment (line 53) says "High-Resolution Hardware Timers". esp_timer resolution is not changed by this. It only enables profiling stats and adds overhead. |
| 57 | `CONFIG_LOG_DEFAULT_LEVEL_INFO=y` | VALID | Runtime default. Combined with the global `-DLOG_LOCAL_LEVEL` (F-04-09). |
| 58 | `CONFIG_LOG_COLORS=y` | VALID | Harmless. |

**Required but ABSENT from sdkconfig.defaults** (each needed for the claims in the docs):

| Missing symbol family | Claimed by | Status |
|---|---|---|
| `CONFIG_SECURE_BOOT=y`, `CONFIG_SECURE_BOOT_V2_ENABLED=y`, signing-key option | `README:41-42`, `SECURITY_SPECIFICATION.md:121`; PIO docs example uses exactly these two symbols | **ABSENT** [VERIFIED] |
| `CONFIG_SECURE_FLASH_ENC_ENABLED=y` (+ RELEASE mode for production) | `README:43`, `SECURITY_SPECIFICATION.md:124` | **ABSENT** [VERIFIED] |
| `CONFIG_NVS_ENCRYPTION=y` | `partitions.csv:12` (`nvs_keys` partition exists) | **ABSENT**; `nvs_keys` is unused by code [VERIFIED grep: no `nvs_flash_secure_init` / `nvs_sec` use] |
| `CONFIG_SPIRAM=y`, `CONFIG_SPIRAM_MODE_OCT=y`, `CONFIG_SPIRAM_SPEED_80M=y` (or 120M per module) | `platformio.ini:3,16` | **ABSENT** (F-04-06) |
| `CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240=y` | `platformio.ini:20`, `main.c:92` | **ABSENT** (F-04-16) [UNVERIFIED default] |
| `CONFIG_ESP_COREDUMP_ENABLE` (+ to-flash) | `partitions.csv:16` (`coredump` partition) | **ABSENT** (F-04-12) [UNVERIFIED name] |
| Application project version / secure version | `main.c:91` hard-codes "v4.0" | **ABSENT** (F-04-10) |

**What a future job must run to confirm the table:**
```bash
# after `idf.py set-target esp32s3 && idf.py reconfigure` in firmware/
# 1) symbols silently dropped from defaults (ENABLED)
grep -E '^CONFIG_[A-Z0-9_]+=' sdkconfig.defaults | cut -d= -f1 | sort -u | while read s; do
  grep -qE "^$s=" build/config/sdkconfig 2>/dev/null || echo "DROPPED-OR-OVERRIDDEN: $s"; done
# 2) disabled-by-n lines
grep -E '^CONFIG_[A-Z0-9_]+=n' sdkconfig.defaults | cut -d= -f1 | while read s; do
  grep -q "^# $s is not set" build/config/sdkconfig || echo "N-NOT-HONORED: $s"; done
# 3) confirm the name exists in IDF source
grep -rn "config SECURE_BOOT_SUPPORTS_PLAINTEXT_BOOTLOADER" $IDF_PATH/components || echo "NO SUCH KCONFIG SYMBOL"
```
[UNVERIFIED: exact `build/config/sdkconfig` path depends on IDF 5.x layout; adjust if it is `build/config/sdkconfig.h`.]

---

### Evidence table E-2: Partition map arithmetic (`firmware/partitions.csv`, sizes in hex and bytes)

Source: `firmware/partitions.csv:9-16`. Bootloader/table region from `partitions.csv:6-7` and `sdkconfig.defaults:10`.

| Region | Start | End (excl.) | Size | Start % 0x1000 / 0x10000 | Flags | Notes |
|---|---|---|---|---|---|---|
| bootloader (reserved, not an entry) | 0x000000 | 0x00C000 | 0xC000 (49,152 B) | ✓ / ✓ | — | `partitions.csv:6` |
| partition table (reserved) | 0x00C000 | 0x00D000 | 0x1000 (4,096 B) | ✓ / ✓ | — | `partitions.csv:7`, `sdkconfig.defaults:10` |
| **unallocated gap A** | 0x00D000 | 0x010000 | 0x3000 (12,288 B) | ✓ / ✗ | — | |
| otadata | 0x010000 | 0x012000 | 0x2000 (8,192 B) | ✓ / ✓ | ota | `partitions.csv:9` (two sectors, correct for OTA data) |
| phy_init | 0x012000 | 0x013000 | 0x1000 (4,096 B) | ✓ / ✗ | phy | `partitions.csv:10` |
| nvs | 0x013000 | 0x019000 | 0x6000 (24,576 B) | ✓ / ✗ | nvs | `partitions.csv:11`. **Not flagged `encrypted`** (F-04-03) |
| nvs_keys | 0x019000 | 0x01A000 | 0x1000 (4,096 B) | ✓ / ✗ | nvs_keys, encrypted | `partitions.csv:12`. Inert (no NVS encryption) |
| **unallocated gap B** | 0x01A000 | 0x020000 | 0x6000 (24,576 B) | ✓ / ✗ | — | |
| ota_0 | 0x020000 | 0x420000 | 0x400000 (4 MiB) | ✓ / ✓ | app | `partitions.csv:13` |
| ota_1 | 0x420000 | 0x820000 | 0x400000 (4 MiB) | ✓ / ✓ | app | `partitions.csv:14`. Starts exactly where ota_0 ends |
| storage | 0x820000 | 0xC20000 | 0x400000 (4 MiB) | ✓ / ✓ | encrypted | `partitions.csv:15`. Unused by code (no spiffs/fatfs/vfs use) |
| coredump | 0xC20000 | 0xC60000 | 0x40000 (256 KiB) | ✓ / ✓ | — | `partitions.csv:16`. Unused (no coredump config) |
| **unallocated tail** | 0xC60000 | 0x1000000 | 0x3A0000 (3,801,088 B = 3.625 MiB) | ✓ / ✓ | — | |

**Totals (all computed by hand from the table; not checked by `gen_esp32part.py`):**
- Overlap check: every region's start equals the previous region's end or is above it. **No overlaps.** [VERIFIED]
- Alignment: every offset and size is a multiple of 0x1000. App slots ota_0/ota_1 and the coredump start are multiples of 0x10000. [VERIFIED]
- Allocated partition entries: 0xA000 (small entries) + 0xC00000 (three 4 MiB regions) + 0x40000 = **0xC4A000 = 12,886,016 B**.
- Unallocated: 0x3000 + 0x6000 + 0x3A0000 = **0x3A9000 = 3,837,952 B** (22.9% of 16 MiB).
- Reserved (bootloader + table): **0xD000 = 53,248 B**.
- Check: 12,886,016 + 3,837,952 + 53,248 = **16,777,216 = 16 MiB** ✓.
- Last used byte: 0xC60000 (12,976,128 B). Tail free: 3,801,088 B.

**Future job:** `python $IDF_PATH/components/partition_table/gen_esp32part.py firmware/partitions.csv /tmp/pt.bin` must complete without error. The script is the authority on app-slot alignment and table size. [UNVERIFIED: not run]

---

### F-04-01 - Secure Boot v2 is not enabled by any config file [P0] [VERIFIED absence, INFERRED impact]

**Evidence**
- `firmware/sdkconfig.defaults:1-58`: no `CONFIG_SECURE_BOOT`, `CONFIG_SECURE_BOOT_V2_ENABLED`, or signing-key symbol (grep returns none).
- `firmware/sdkconfig.defaults:12-15`: section header says "Secure Boot v2" but contains only rollback/anti-rollback and the mis-named line 15 (see E-1).
- `firmware/README.md:41-42` and `firmware/SECURITY_SPECIFICATION.md:121-122` claim RSA-3072 Secure Boot v2 for the bootloader.
- `firmware/SECURITY_SPECIFICATION.md:153`: the checkbox "Flash Encryption & Secure Boot v2: signing keys created" is **unchecked** (`- [ ]`). The spec itself does not claim completion.
- PlatformIO documented enable pattern (`https://docs.platformio.org/en/latest/frameworks/espidf.html`): `CONFIG_SECURE_BOOT=y` and `CONFIG_SECURE_BOOT_V2_ENABLED=y`. Neither is present here.

**Failure mode + trigger:** Image is unsigned at the bootloader level. Any party with UART/USB access (download mode is not disabled, F-04-04) can flash a modified app into ota_0/ota_1.
**Consequence:** Modified firmware can drive PROFET (`board_pins.c:66-68`), starter SSR (`board_pins.c:80`), and kill SSR (`board_pins.c:90`). This is theft-enabling and safety-relevant. P0 applies if this build ships; prototype status is not stated as shipping.
**Fix sketch:** Add a production sdkconfig (e.g., `sdkconfig.prod.defaults`, selected via `SDKCONFIG_DEFAULTS` in a PIO env) with `CONFIG_SECURE_BOOT=y`, `CONFIG_SECURE_BOOT_V2_ENABLED=y`, and a signing-key option pointing to a key outside the repo. Keep the dev build separate and clearly labelled.
**Verification (future job):**
```bash
idf.py reconfigure && grep -E 'CONFIG_SECURE_BOOT(_V2_ENABLED)?=' build/config/sdkconfig
espsecure.py verify_signature --version 2 --keyfile <pubkey.pem> build/bootloader/bootloader.bin  # expect OK
espefuse.py --chip esp32s3 summary   # after a lab burn: SECURE_BOOT_EN=1 on a test device only
```
[UNVERIFIED: `espsecure`/`espefuse` argument syntax for the installed IDF version.]

---

### F-04-02 - Flash encryption is not enabled; `encrypted` partition flags are inert without it [P0] [VERIFIED absence, INFERRED semantics]

**Evidence**
- `partitions.csv:12` (`nvs_keys ... encrypted`) and `partitions.csv:15` (`storage ... encrypted`).
- `sdkconfig.defaults`: no `CONFIG_SECURE_FLASH_ENC_ENABLED` or mode symbol.
- `firmware/README.md:43` and `SECURITY_SPECIFICATION.md:124` claim AES-XTS flash encryption protects certs/keys.
- `SECURITY_SPECIFICATION.md:153` checklist item unchecked.

**Failure mode + trigger:** Without flash encryption, the `encrypted` flag does nothing [INFERRED from IDF semantics, UNVERIFIED here]. Flash can be dumped with `esptool read_flash` (reachable while download mode and JTAG are open; see F-04-04).
**Consequence:** Any secret stored in flash is readable: NVS bonds (`BT_NIMBLE_MAX_BONDS=5`, `sdkconfig.defaults:37`), any future mTLS key or HMAC secret. Cloning a device's identity is then possible.
**Fix sketch:** Enable `CONFIG_SECURE_FLASH_ENC_ENABLED=y` in the production sdkconfig. Use RELEASE mode only after a lab-validated flow on a sacrificial chip (RELEASE burns eFuses irreversibly). Keep `encrypted` on storage/nvs_keys.
**Verification (future job):** After a lab burn, `espefuse.py summary` shows `SPI_BOOT_CRYPT_CNT` set; `esptool read_flash` of the `storage` region returns ciphertext. [UNVERIFIED: exact field names and mode symbol names.]

---

### F-04-03 - NVS (the credential store) is plaintext: not flagged encrypted and NVS encryption is off [P1] [VERIFIED]

**Evidence**
- `partitions.csv:11`: `nvs, data, nvs, 0x13000, 0x6000,` has **no** `encrypted` flag.
- `main.c:96` comment: NVS is for "Güvenlik anahtarları" (security keys) and pairings. Pairings (NimBLE bonds, `sdkconfig.defaults:37`) and keys are stored there.
- `nvs_keys` (`partitions.csv:12`) exists but no `CONFIG_NVS_ENCRYPTION` and no `nvs_flash_secure_init` in code (grep: zero hits).

**Failure mode + trigger:** Even with flash encryption later enabled, an unflagged `nvs` partition is not encrypted [INFERRED]. And the keys partition is unused.
**Consequence:** BLE bond keys and any stored device secret are readable from a flash dump.
**Fix sketch:** Mark `nvs` as `encrypted` (with FE on), or enable `CONFIG_NVS_ENCRYPTION=y` with `nvs_keys` encrypted; either way, decide and document which. Pick one and verify.
**Verification (future job):** After flashing, `esptool read_flash <nvs-offset> 0x6000` and search for a known bond/key string. Must not be found in plaintext.

---

### F-04-04 - Production provisioning path is absent: no signing keys, eFuse burn, JTAG/download lock, or per-device identity [P1] [VERIFIED absence]

**What exists in-repo (all of it):**
- Configuration fragments only (above). No eFuse script: `grep -rn 'espefuse\|espsecure\|efuse' .` returns no source hits outside a BOM/report false positive.
- No signing key or `.pem` in the tree (`find` returns none).
- Doc checklist: `SECURITY_SPECIFICATION.md:151-154` (mTLS script, signing keys, eFuse script) — all three unchecked, and the scripts do not exist.
- `SECURITY_SPECIFICATION.md:125` lists `DIS_PAD_JTAG`, `DIS_USB_JTAG`, `DIS_DOWNLOAD_MODE` as the intended lock; no code or script sets them.

**What is missing (checklist, with the artifact each needs):**
| Item | Required artifact | Status |
|---|---|---|
| Secure Boot signing key | `secure_boot_signing_key.pem` generated outside repo, stored in HSM/vault | Missing [VERIFIED] |
| SB digest eFuse burn | `espefuse.py burn_key_digest` step script | Missing |
| Flash-encryption first boot | RELEASE-mode burn, `SPI_BOOT_CRYPT_CNT` step | Missing |
| JTAG / download lock | `DIS_*` eFuse burn script | Missing |
| device_id derivation | None in code. `PROJECT.md:88` example `ESP32_A8B6C4` suggests MAC-derived. `grep esp_read_mac` = 0 hits | Missing |
| Per-device X.509 client cert + key | Provisioning tool writing to a defined partition | Missing (see F-04-07) |
| Anti-rollback burn | secure-version eFuse procedure | Missing (see F-04-05) |

**Failure mode:** Production units are built and flashed by hand, with no reproducible step that burns SB digest, FE, or JTAG locks. Irreversible eFuse steps are error-prone when improvised.
**Fix sketch:** Write `firmware/provisioning/` with: key-generation doc (keys out of repo), a `burn_efuses.sh` with dry-run and explicit `--i-understand-irreversible` flag, a per-device provisioning script (device_id + cert + key into a named partition), and a test on a sacrificial chip.
**Verification (future job):** Dry-run the burn script against a test chip; `espefuse.py summary` diffs before/after match the expected table.

---

### F-04-05 - Anti-rollback is configured with no secure-version scheme or burn procedure [P1] [UNVERIFIED semantics]

**Evidence:** `sdkconfig.defaults:14` `CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK=y`. No secure-version field or value is set anywhere (grep `secure_version|SEC_VER` = 0 hits). `main.c:72-86` is the OTA self-test (rollback), which is a different and reversible mechanism.

**Failure mode + trigger:** Anti-rollback (eFuse-based, irreversible) and app rollback (`main.c:72-86`, reversible) are conflated in the docs (`firmware/README.md:45-48` describes only the reversible one). If anti-rollback is later enabled with an unmanaged security version, a single bad release can permanently block downgrades, or a reset to an old version can be used to load a vulnerable image.
**Consequence:** Either no protection against downgrade attacks (current state), or an irreversible lock-in on a bad version (after enabling).
**Fix sketch:** Document the two mechanisms separately. Define the security-version policy (who bumps, when). Only burn after the policy is written and a test device is validated.
**Verification (future job):** `grep -rn 'secure_version\|SEC_VER' $IDF_PATH/components/bootloader_support` to find the field name; build a test image and check `esp_app_desc` `secure_version` after build. [UNVERIFIED names.]

---

### F-04-06 - No octal PSRAM configuration; board id and comments claim 8 MB octal PSRAM [P2] [VERIFIED absence]

**Evidence**
- `platformio.ini:3` and `:16`: "16MB Flash, 8MB Octal PSRAM" / "8MB Octal OPI PSRAM".
- `platformio.ini:14`: `board = esp32-s3-devkitc-1`. PlatformIO's own table lists `ESP32-S3-DevKitC-1-N8 (8 MB QD, No PSRAM)` under that board family [VERIFIED: PIO espressif32 docs, Debug table].
- `sdkconfig.defaults`: zero `CONFIG_SPIRAM*` symbols.
- `sim/renode/automoto.repl:7-15`: memory map has `instram0`, `dataram0`, and `flash` only. **No PSRAM region is modelled.** `sim/wokwi/diagram.json:7,11` uses `board-esp32-s3-devkitc-1` with `flashSize: 16` and no PSRAM attribute.
- PIO PSRAM doc for espidf is only `-DCONFIG_SPIRAM_CACHE_WORKAROUND` [VERIFIED PIO docs]. It does not enable PSRAM.
- `hardware/production/automoto_bom_jlcpcb.csv:2` and `PCB_SPECIFICATION.md:88` claim 8 MB PSRAM on the BOM module. The LCSC part number was not verified [UNVERIFIED].

**Octal mode requirements that are missing** (IDF 5.x names, to confirm):
- `CONFIG_SPIRAM=y` (enable external RAM)
- `CONFIG_SPIRAM_MODE_OCT=y` (octal, not quad)
- `CONFIG_SPIRAM_SPEED_80M=y` (or 120M if the module datasheet allows it) [UNVERIFIED module rating]
- Pin constraint: octal PSRAM occupies GPIO 33–37 on N16R8. `board_pins.h:18-49` uses none of GPIO 33–37 (VERIFIED), so there is no pin conflict today. [INFERRED from module datasheet; confirm on the Espressif N16R8 datasheet]
- Board id: `esp32-s3-devkitc-1` is the N8 devkit family per PIO docs; the custom module should be documented, or a custom board JSON used. Cosmetic for espidf, since sdkconfig sets flash size.

**Failure mode + trigger:** Only internal SRAM (~320 KB) is used. Tasks at `main.c:131-132` use 4 KB stacks. NimBLE is pinned to internal memory (`sdkconfig.defaults:35`). When TLS/MQTT (`PROJECT.md:84-101`) lands, internal heap pressure is likely.
**Consequence:** Either 8 MB is paid for and unused, or the future TLS/MQTT stack hits heap exhaustion at runtime.
**Fix sketch:** Decide whether PSRAM is needed. If yes, add the four symbols to the production sdkconfig and a `CONFIG_SPIRAM_USE_MALLOC` decision. If no, fix the README/platformio.ini claims.
**Verification (future job):** `idf.py reconfigure && grep 'CONFIG_SPIRAM' build/config/sdkconfig`; on hardware, `heap_caps_get_total_size(MALLOC_CAP_SPIRAM)` must be non-zero.

---

### F-04-07 - Where client.crt / client.key live is undefined; NVS erase path can silently wipe them [P1] [VERIFIED]

**Evidence**
- No certificate, key, or TLS code in `firmware/main` (grep for `cert|x509|mbedtls_x509|esp_tls` = 0 hits, excluding the unused mbedtls config symbols).
- `PROJECT.md:184` puts `certs/` on the **server** side, not the device.
- `SECURITY_SPECIFICATION.md:76` says each device needs `client.crt` and `client.key` at production time. No partition or path is specified.
- Candidate locations and their status:
  - **nvs** (`partitions.csv:11`, 24 KB): capacity is sufficient (see below) but plaintext (F-04-03).
  - **storage** (`partitions.csv:15`, 4 MB, `encrypted`): would be correct for keys if FE is on, but no filesystem code exists.
  - Embedding in the image (`board_build.embed_txtfiles`, documented by PIO): wrong, because certs are per-device and would be the same in every OTA image.
- **Capacity check (INFERRED):** A P-256 client cert plus key plus CA chain is roughly 2–4 KB PEM. NVS 0x6000 = 24 KB = 6 pages of 4 KB, which holds those blobs with room for ~5 NimBLE bonds. Fits.
- **NVS erase hazard:** `main.c:97-102`:
  ```c
  esp_err_t ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
  ```
  `ESP_ERR_NVS_NEW_VERSION_FOUND` occurs when an older firmware reads NVS written by a newer one. This happens after an OTA downgrade or rollback (see F-04-05 / `main.c:72-86`). The code then **erases the entire NVS partition**, including any provisioned identity and bonds. No log of which keys were lost, no guard.

**Failure mode + trigger:** Rollback to an older firmware slot (automatic on boot failure per `README:46-48`) → NVS version mismatch → full erase.
**Consequence:** Device loses its identity and bonds; a recovery path is not defined. This is a silent, self-inflicted provisioning wipe.
**Fix sketch:** Store identity in a separate partition (not NVS) that is never erased by the app. Replace the unconditional erase with a guarded path that refuses to erase provisioned data and reports the failure.
**Verification (future job):** Flash new image, provision a dummy key into nvs, roll back via a forced boot failure, observe whether the key survives.

---

### F-04-08 - Unknown Kconfig symbols are silently dropped; three lines already suspect [P1] [VERIFIED mechanism per task brief, UNVERIFIED per-IDF]

**Evidence:** Lines flagged in E-1 as WRONG or SUSPICIOUS: `sdkconfig.defaults:4` (target pin), `:15` (non-existent symbol, assumed), `:43` (ineffective), `:53-54` (misleading comment and profiling flag).

**Failure mode + trigger:** A misspelled or non-existent `CONFIG_*` in `sdkconfig.defaults` does not fail the build. The defaults file is applied, the symbol is absent from the generated config, and the intended feature silently stays off. Line 15 is the example: the team believes Secure Boot is partially configured, and nothing enables it.
**Consequence:** Silent loss of security features with no error. The loss is only visible if someone diffs the generated config.
**Fix sketch:** Add a CI check (see the job in E-1) that fails if any `CONFIG_` line in `sdkconfig.defaults` is not present in the generated config. Gate production builds on it.
**Verification (future job):** The three-step grep script in E-1 must print zero `DROPPED` / `N-NOT-HONORED` lines for the production defaults file.

---

### F-04-09 - `build_flags` define CONFIG_ and CORE_DEBUG_LEVEL macros outside Kconfig [P2] [VERIFIED lines; INFERRED effect]

**Evidence:** `platformio.ini:29-32`:
```ini
build_flags =
    -DCORE_DEBUG_LEVEL=3
    -DLOG_LOCAL_LEVEL=ESP_LOG_INFO
    -DCONFIG_NIMBLE_ENABLED=1
```
- `CORE_DEBUG_LEVEL` is an Arduino-core macro only. PIO documents it under `framework = arduino` [VERIFIED PIO Debug Level section]. With `framework = espidf` it does nothing [INFERRED; confirm `grep -rn CORE_DEBUG_LEVEL $IDF_PATH` = 0 hits].
- `CONFIG_NIMBLE_ENABLED` is not, to my knowledge, an ESP-IDF 5.x symbol; the NimBLE symbol is `CONFIG_BT_NIMBLE_ENABLED` (`sdkconfig.defaults:33`). Confirm: `grep -rn 'config NIMBLE_ENABLED' $IDF_PATH/components` expecting zero hits. [UNVERIFIED]
- `LOG_LOCAL_LEVEL=ESP_LOG_INFO` is applied globally, so every `ESP_LOGD`/`ESP_LOGV` in every component (including IDF) is compiled out at compile time (`ble_keyless.c:22`, `power_manager.c:18`). This is independent of `CONFIG_LOG_DEFAULT_LEVEL_INFO` (`sdkconfig.defaults:57`) and cannot be changed in menuconfig.

**Why defining CONFIG_ macros via -D is dangerous (general):**
1. **Bypasses dependency resolution.** Kconfig would reject or auto-select dependent options; `-D` sets the flag with no checks.
2. **Invisible to menuconfig and sdkconfig.** The generated `sdkconfig` can say `n` while code compiles with the `-D` value. Two translation units can disagree.
3. **Redefinition conflicts.** `sdkconfig.h` defines `CONFIG_*` macros, so a `-D` of the same name produces redefinition warnings or silently keeps one value [UNVERIFIED for this IDF version].
4. **Stale builds.** Changing sdkconfig does not force recompilation of files built with the `-D`, so the binary can disagree with the config file.
5. **Unreviewable.** The effective configuration is split between two files, and the reviewer of `sdkconfig.defaults` sees an incomplete picture.

**Consequence:** Debug visibility is reduced for every component, and the config split makes reviews of security settings unreliable.
**Fix sketch:** Delete the three `build_flags` lines. Set the log level in sdkconfig (`CONFIG_LOG_DEFAULT_LEVEL`, `CONFIG_LOG_MAXIMUM_LEVEL`). Drop `CORE_DEBUG_LEVEL` entirely.
**Verification (future job):** After the change, `grep -E 'CONFIG_NIMBLE_ENABLED|CORE_DEBUG_LEVEL|LOG_LOCAL_LEVEL' .pio/build/esp32s3/compile_commands.json` returns nothing (for PIO) and `ninja -t commands | grep -c -- '-D'` drops by 3 per file.

---

### F-04-10 - PlatformIO build path: `custom_sdkconfig_defaults` is not a documented option, so `sdkconfig.defaults` may not apply [P1] [VERIFIED docs, UNVERIFIED runtime]

**Evidence**
- `platformio.ini:35`: `custom_sdkconfig_defaults = sdkconfig.defaults`.
- PlatformIO Espressif 32 docs (`https://docs.platformio.org/en/latest/platforms/espressif32.html`), section "sdkconfig Configuration (ESP-IDF)", document exactly two mechanisms:
  - `board_build.esp-idf.sdkconfig_path` to set where the generated sdkconfig is written.
  - `board_build.cmake_extra_args = -DSDKCONFIG_DEFAULTS="sdkconfig.common;sdkconfig.board"` to layer defaults files.
  - `custom_sdkconfig_defaults` appears in neither the docs I fetched nor the PIO espidf docs.
- The docs say PIO generates `sdkconfig.<env>` (here `sdkconfig.esp32s3_automoto`), not `sdkconfig`. That file is not in `.gitignore` (see F-04-13).

**Failure mode + trigger:** `pio run` runs with PIO's default defaults. The project's `sdkconfig.defaults` is never applied, because PlatformIO does not read the custom key. The result: no TWDT settings, NimBLE settings, custom partition offset (the partition file is set separately via `board_build.partitions`, so partitions alone may still apply), or flash mode from the defaults file.
**Consequence:** The PIO build and the `idf.py` build (`README:61-67`) produce different binaries from one source. The sim (`sim/README.md:48`) loads `firmware/.pio/build/esp32s3/firmware.elf`, so the simulated binary may not be the release configuration.
**Fix sketch:** Replace line 35 with `board_build.cmake_extra_args = -DSDKCONFIG_DEFAULTS="sdkconfig.defaults"` (or the explicit file list). Keep one defaults file for both build systems.
**Verification (future job):**
```bash
cd firmware && pio run -v 2>&1 | grep -i 'SDKCONFIG_DEFAULTS\|sdkconfig'
diff <(grep '^CONFIG_' .pio/build/esp32s3/sdkconfig* 2>/dev/null | sort) <(grep '^CONFIG_' build/config/sdkconfig | sort)
```
Expect zero diff on security-relevant symbols after the fix. [UNVERIFIED: exact PIO-generated file names.]

---

### F-04-11 - `src_dir = main` with `framework = espidf` and a root CMakeLists: what PIO builds is unverified [P2] [UNVERIFIED]

**Evidence**
- `platformio.ini:9`: `src_dir = main`.
- `firmware/CMakeLists.txt:5`: `include($ENV{IDF_PATH}/tools/cmake/project.cmake)`. That is the idf.py entrypoint.
- `firmware/main/CMakeLists.txt:2-25`: `idf_component_register(SRCS ... INCLUDE_DIRS "." REQUIRES ...)`. All 8 `.c` files in `main/` are listed (VERIFIED by directory listing).

**Analysis:**
- For `idf.py`, the root CMake drives the build and `main/` is the main component. Consistent.
- For PlatformIO's espidf framework, PIO generates its own top-level project and treats `src_dir` as the source tree. Setting `src_dir = main` makes `main/` the PIO source folder, so the `main/CMakeLists.txt` (`idf_component_register`) may be used directly as the main component. That matches the intent.
- The root `firmware/CMakeLists.txt` is most likely **ignored by PIO** [UNVERIFIED]. So there is no direct conflict, but two build drivers share one component and the `IDF_PATH` env var (`firmware/CMakeLists.txt:5`) is needed only for idf.py.
- Risk: PIO may place `main/` under a generated `src` component name or compile with a different project name. Symptoms would be duplicate symbols or a missing `app_main` only in one path.

**Consequence:** Unknown which sources and components PIO compiles. The only confirmed artifact is `main/CMakeLists.txt`.
**Fix sketch:** Pick one primary build driver for release (recommend idf.py). Keep PIO as dev convenience and make the release build use idf.py with the production defaults file.
**Verification (future job):** `pio run -v` and then `grep -c 'main.c\|ble_keyless.c' .pio/build/esp32s3/compile_commands.json` must list all 8 sources exactly once. Also `diff` the component list from `idf.py build` vs PIO (`build/project_description.json`).

**Answer to the brief's question directly:** `src_dir = main` + `main/CMakeLists.txt` is not an obvious conflict, but the build outcome under PIO is UNVERIFIED. The root `firmware/CMakeLists.txt` is most likely not used by PIO.

---

### F-04-12 - CMake REQUIRES audit: listed-but-unused, used-but-implicit, and missing-for-planned-work [P2] [VERIFIED for includes; UNVERIFIED for component ownership]

**Evidence: REQUIRES in `firmware/main/CMakeLists.txt:13-25` vs includes in `firmware/main/*.c|*.h`.**

| Component listed | Used by code (include or call) | Status |
|---|---|---|
| nvs_flash | `main.c:4`, `main.c:97-102` | Used. Keep. |
| esp_timer | `failsafe.c:6`, `ble_keyless.c:4`, `ble_keyless.c:27` | Used. Keep. |
| driver | `board_pins.h:6` (`driver/gpio.h`), `sensors_imu.c:4` (`driver/i2c.h`), `modem.c:4` (`driver/uart.h`) | Used. Keep. |
| freertos | `main.c:7-8`, `actuator_safety.c:5-7`, `failsafe.c:4-5`, `modem.c:5-6` | Used. Keep. |
| bt | No NimBLE or `esp_bt` include anywhere. `ble_keyless.c:1-29` has no NimBLE API | **Listed but unused.** Build cost with no code. Keep only when NimBLE calls land. |
| esp_pm | No `esp_pm.h` include; `CONFIG_PM_ENABLE` set but no `esp_pm_configure` | **Listed but unused.** |
| mbedtls | No mbedtls include in `firmware/main` | **Listed but unused** until TLS lands. |
| esp_partition | `esp_partition_t` used via `esp_ota_ops.h` (`main.c:72`); no direct include | Used transitively. Harmless; keep explicit or remove [UNVERIFIED]. |
| esp_event | No `esp_event.h` include | **Listed but unused.** |
| app_update | `main.c:5` (`esp_ota_ops.h`), `main.c:72-86` | Used. Keep. |
| esp_system | `main.c:6`, `actuator_safety.c:4` (`esp_task_wdt.h`) | Used. Keep. |
| log | `esp_log.h` in all `.c` | Used. Keep. |

**Used but NOT listed (relies on transitive REQUIRES):**
- `esp_random.h`: `ble_keyless.c:5`, `esp_fill_random` at `ble_keyless.c:26` (a security-relevant nonce source). Not listed; likely provided through another component [UNVERIFIED: in IDF 5.x it is in `esp_hw_support`]. Confirm: `grep -rn esp_random.h $IDF_PATH/components/*/include` and run `idf.py reconfigure` with `REQUIRES` trimmed to see what breaks.
- `esp_sleep.h`: `power_manager.h:7`, used at `power_manager.c:15-51`. Not listed; likely `esp_hw_support` or `esp_system` [UNVERIFIED].
- `esp_err.h`, `esp_task_wdt.h` are covered above.

**Missing for planned or current functionality:**
- `esp_adc` (or `esp_adc/adc_oneshot.h`): `board_pins.h:26` documents `PIN_PROFET_IS` as `ADC1_CHANNEL_9`, but no ADC call exists. Needed once current sense is implemented.
- `mqtt` / `esp_mqtt`: `PROJECT.md:84-101` plans MQTT; `PROJECT.md:173` lists `mqtt_handler.h`. None exists. Needed for Phase 4 (`PROJECT.md:199`).
- `esp_http_client`: no HTTP in the current plan. Not needed; not flagged.
- `driver/i2c.h` is the legacy I2C driver. In newer IDF 5.x releases it is deprecated in favour of `driver/i2c_master.h` [UNVERIFIED version]. P3 deprecation risk.

**Consequence:** Build surface is larger than necessary (bt, mbedtls, esp_pm, esp_event). Implicit includes will break silently when a transitive dependency moves.
**Fix sketch:** Trim REQUIRES to what is used; list `esp_random`, `esp_sleep`, `esp_hw_support` explicitly where used; add `esp_adc`/`mqtt` when the feature lands.
**Verification (future job):** `idf.py build` with each unused component removed one at a time must still link. Any failure identifies a real use.

---

### F-04-13 - Partition map: unused coredump and storage partitions, 3.6 MiB unallocated tail, and no coredump config [P2] [VERIFIED]

**Evidence:** `partitions.csv:15-16` (storage 4 MiB and coredump 256 KiB). No `spiffs`/`fatfs`/`esp_vfs` use in code (VERIFIED grep). No `CONFIG_ESP_COREDUMP*` in `sdkconfig.defaults`. Unallocated 3,801,088 B tail plus 36,864 B of gaps (E-2).

**Failure mode + trigger:** Post-crash diagnostics are impossible in the field: coredump partition exists but is never written. Storage partition is reserved but no code uses it, so certs/keys (F-04-07) have no defined home.
**Consequence:** Debuggability gap (P2). Wasted flash that could hold a third slot or certs (P3).
**Fix sketch:** Decide a certs/identity partition (dedicated `cert`, `encrypted`), enable a coredump target in sdkconfig, and document the tail.
**Verification (future job):** `gen_esp32part.py` (E-2) plus `esptool image_info` on the app after the change.

---

### F-04-14 - README claims TWDT panic forces relays to a safe state; configuration does not do that [P2] [VERIFIED claim vs config; INFERRED hardware behavior]

**Evidence:** `firmware/README.md:38`: "Donanımsal watchdog anında panic üreterek tüm röleleri 0 (açık / güvenli pasif) seviyesine çeker ve çipi resetler" ("on TWDT trigger, panic sets all relays to 0 (open/safe) and resets the chip"). `sdkconfig.defaults:23` sets `CONFIG_ESP_TASK_WDT_PANIC=y`, which only panics and resets. No code runs in the panic path; `board_pins.c` GPIO writes are not in any handler.

**Failure mode + trigger:** A hung actuator task causes a reset. GPIO output state during and after reset is determined by the ESP32-S3 reset default pull state and the external circuit, not by firmware [INFERRED].
**Consequence:** The documented safe state is not guaranteed by the firmware config. The hardware (pull-downs, NO topology per `SECURITY_SPECIFICATION.md:141-143`) must provide it. Cross-ref to the hardware audit task.
**Fix sketch:** Reword README:38 to say the safe state depends on hardware pull-down topology, or add a panic-time GPIO reset via a documented hook (e.g., `esp_register_shutdown_handler`) if IDF supports it for this path [UNVERIFIED].
**Verification (future job):** Power-cycle/hang test with a logic analyzer on `SSR_KILL`, `SSR_STARTER`, `PROFET_IN` (`board_pins.h:22-24`) during forced TWDT trip.

---

### F-04-15 - 0xC000 partition-table offset implies a 48 KiB bootloader budget; RSA-3072 Secure Boot v2 fit is UNVERIFIED [P2] [INFERRED]

**Evidence:** `sdkconfig.defaults:10` (`CONFIG_PARTITION_TABLE_OFFSET=0xC000`), `partitions.csv:6-7` (comment: "0x0000 - 0xC000 : Secure Boot v2 Bootloader (Genişletilmiş 48 KB Alan)"), `firmware/README.md:42` ("48 KB bootloader marjı", "RSA-3072 ... 32-48 KB").

**Analysis:**
- Offset 0xC000 = 49,152 B. Everything before 0xC000 is bootloader image plus its Secure Boot v2 signature sector.
- Secure Boot v2 appends a signature block (4 KB, aligned) after the bootloader image [UNVERIFIED size]. An RSA-3072 digest lives in eFuse, not in the image.
- The IDF default partition offset is 0x8000 (32 KB) [UNVERIFIED]. 0xC000 is 16 KB more headroom, which is a sound choice.
- The "32–48 KB" range in the README is not sourced. The real number is in `build/bootloader/bootloader.bin` after a build, plus 4 KB for the signature sector. The build fails if the bootloader is too large for the offset [UNVERIFIED], so overflow is loud, not silent.

**Failure mode + trigger:** A future bootloader change (new log features, larger component set) grows the image past 0xC000 − 4 KB and the build fails. Or the developer lowers the offset to save space.
**Consequence:** Build break (loud). No silent security loss. Documentation says more than is verified.
**Fix sketch:** Record the measured bootloader size in the build report. Remove the unsourced "32–48 KB" claim, or cite the IDF doc that states it.
**Verification (future job):** `ls -l build/bootloader/bootloader.bin` plus 4096 must be ≤ 0xC000 (49,152). Expected to fit; not measured here.

---

### F-04-16 - CPU frequency 240 MHz is claimed but not set in sdkconfig [P2] [UNVERIFIED default]

**Evidence:** `platformio.ini:20` `board_build.f_cpu = 240000000L`; `main.c:92` log "Dual-Core 240MHz"; `firmware/README.md:5-6` describes a 240 MHz target. No `CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240` in `sdkconfig.defaults` (VERIFIED).

**Failure mode + trigger:** The `idf.py` build uses the IDF default CPU frequency, which I believe is 160 MHz for ESP32-S3 [UNVERIFIED]. The PIO setting may or may not reach sdkconfig (depends on PIO's espidf builder, unverified).
**Consequence:** Performance and timing budgets (e.g., the 18 ms RTT threshold, `SECURITY_SPECIFICATION.md:62`, and the 20 ms loop, `actuator_safety.c:28`) are based on a frequency the idf.py build may not use.
**Fix sketch:** Add `CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240=y` to the defaults file.
**Verification (future job):** `grep CPU_FREQ build/config/sdkconfig` must show 240.

---

### F-04-17 - Reproducibility: no CI, no lockfile, unpinned platform and ESP-IDF, hard-coded version string [P1] [VERIFIED absence]

**Evidence**
- No CI: no `.github/`, no `.gitlab-ci.yml`, no workflow file anywhere in the repo (`find` for `*.yml`, `*.yaml`, `.github` = 0 hits).
- No lockfile: no `platformio.lock`, no `*.lock`, no pinned `platform_packages` in `platformio.ini`.
- Unpinned platform: `platformio.ini:12` `platform = espressif32` with no version. PIO docs warn the latest stable is "NOT recommended" and recommend `espressif32@x.y.z` [VERIFIED PIO docs, "Stable and upstream versions"].
- Unpinned ESP-IDF: the version appears only as prose ("ESP-IDF v5.x", `firmware/README.md:3`; "v5.1+", `SECURITY_SPECIFICATION.md:148`). No `IDF_VERSION`, no `.tool-versions`, no `requirements.txt`.
- Hard-coded version: `main.c:91` "AutoMoto Smart Security & Telemetry Platform v4.0". Not read from the build. No `esp_app_get_description` / `esp_app_desc` use. The root `project(automoto_firmware)` (`firmware/CMakeLists.txt:7`) sets no `PROJECT_VER`.
- `.gitignore:1-22` does not exclude `build/`, `.pio/`, `sdkconfig.*`, `*.pem`, `*.key`. Generated build state can be committed by accident.

**Failure mode + trigger:** Two engineers build the same commit and get different toolchains, different IDF patch levels, and a different binary. The version string shown at boot is the same for every build.
**Consequence:** A released binary cannot be reproduced or traced to a commit. Rollback/anti-rollback (F-04-05) needs a monotonic version that does not exist.
**Fix sketch:** Pin `espressif32@<version>` and an ESP-IDF version (`IDF_VERSION` file plus PIO `framework-espidf` pin). Add a CI job that runs `idf.py build` with the production defaults. Stamp the app version from `git describe` via `PROJECT_VER`, and print it from `esp_app_get_description()`. Add `build/`, `.pio/`, `sdkconfig.*`, `*.pem`, `*.key`, `*.crt` to `.gitignore`.
**Verification (future job):** Two clean-checkout builds from the same commit produce byte-identical `firmware.bin` (`sha256sum`), and the boot log shows the git describe string.

---

### F-04-18 - Key-material hygiene: no `.gitignore` protection for signing keys [P2] [VERIFIED]

**Evidence:** `.gitignore:1-22` contains no `*.pem`, `*.key`, `*.crt`, or `secure_boot_signing_key*` rule. Repo-wide search for those extensions returns zero files today (VERIFIED), so this is a latent risk, not a current leak.

**Failure mode + trigger:** A developer generates the SB signing key inside the project tree (IDF's default output location) and runs `git add .`.
**Consequence:** Theft of the signing key enables malicious signed firmware to pass SB v2 on every device signed with that key.
**Fix sketch:** Add the patterns above. Document that keys are generated and stored outside the repo (F-04-04).
**Verification (future job):** `git check-ignore -v firmware/secure_boot_signing_key.pem` must report a match.

---

### F-04-19 - Board id, module naming, and hardware CAD drift (WROOM-1U-N16R8 vs WROOM-1 vs WROOM-32U) [P3] [VERIFIED]

**Evidence:**
- `platformio.ini:14`: `esp32-s3-devkitc-1` (N8 devkit family per PIO docs; see F-04-06).
- `PROJECT.md:59` says "ESP32-S3-WROOM-1" (no U). `hardware/pcb/PCB_SPECIFICATION.md:88` and `hardware/production/automoto_bom_jlcpcb.csv:2` say "ESP32-S3-WROOM-1U-N16R8".
- `hardware/pcb/generate_kicad_pcb.py:135` loads `RF_Module.3dshapes/ESP32-WROOM-32U.step` — the **original ESP32** 3D model, not S3 (VERIFIED line; the shape-file mismatch is the hardware task's area).
- `hardware/pcb/drawings/generate_drawings.py:79` prints "ESP32-S3-WROOM-1-N16R8" (no U).

**Consequence:** Documentation and CAD disagree on the exact module. Cosmetic for firmware, but a wrong 3D model can cause a mechanical or antenna-keepout error (cross-ref hardware audit).
**Fix sketch:** Pick one module name everywhere; fix the 3D model reference to the S3 1U part.
**Verification:** Grep for `WROOM-1` vs `WROOM-1U` returns one spelling; KiCad 3D viewer shows the S3 module.

---

### F-04-20 - Documentation drift in build layout and feature claims [P3] [VERIFIED]

**Evidence:**
- `PROJECT.md:169-179` describes `firmware/include/`, `firmware/src/main.cpp`, and `modem_sim7080.h`/`mqtt_handler.h`. The repo has `firmware/main/*.c` and `modem.h`; no `include/`, `src/`, or `mqtt_handler.h` exists.
- `firmware/README.md:5` claims the hybrid PIO/IDF setup is for "CI/CD". No CI exists (F-04-17).
- `firmware/README.md:2-3` / `SECURITY_SPECIFICATION.md:146-154` present the production checklist as in-progress; the checkboxes are unchecked. That is honest, but the README's "Secure Boot v2 hazırlığı" (line 41) reads as more finished than it is.

**Consequence:** Reviewers and new contributors build the wrong mental model. Low direct risk.
**Fix sketch:** Update PROJECT.md tree to match the repo; remove "CI/CD" from README until CI exists; reword the "hazırlığı" (preparation) claims to "planned".
**Verification:** Doc diff review.

---

## Open Questions
1. **Does PIO honor `custom_sdkconfig_defaults` at all?** Confirm with `pio run -v` and a diff of the generated sdkconfig (F-04-10). If yes, F-04-10 is downgraded to P3 but the docs still need fixing.
2. **Is `CONFIG_SECURE_BOOT_SUPPORTS_PLAINTEXT_BOOTLOADER` a real IDF 5.x symbol?** `grep -rn SUPPORTS_PLAINTEXT_BOOTLOADER $IDF_PATH/components` (E-1). If it exists, what does it gate?
3. **Which IDF version is intended?** "v5.x" / "v5.1+" (`README:3`, `SECURITY_SPECIFICATION.md:148`). Verdicts in E-1 are for IDF 5.x in general; a specific version may change names (e.g., anti-rollback, ESP_SLEEP symbols).
4. **Is the 8 MB PSRAM real on the populated module?** The BOM says N16R8 (`automoto_bom_jlcpcb.csv:2`); the LCSC part and the physical chip were not checked. Read the printed marking on a real module.
5. **Does the device need PSRAM for the planned TLS/MQTT stack?** If yes, F-04-06 becomes P1.
6. **Where should client cert/key live?** A design decision (nvs+NVS_ENCRYPTION vs dedicated encrypted partition vs DS peripheral). Recommend the decision is recorded before any provisioning code is written.
7. **Is ESP-IDF's `esp_random` valid for the nonce with BT enabled?** Assumed yes (INFERRED from `sdkconfig.defaults:31`); confirm against the ESP-IDF RNG documentation.

## Suggested Jobs
1. **Build-validation job (CI, pinned IDF):** run `idf.py set-target esp32s3 && idf.py reconfigure && idf.py build` with a pinned IDF. Then run the E-1 drop-detection script and the `gen_esp32part.py` check (E-2). Fail on any DROPPED/N-NOT-HONORED line.
2. **PIO parity job:** `pio run` with `board_build.cmake_extra_args -DSDKCONFIG_DEFAULTS=...` (F-04-10). Diff generated config against the idf.py build; fail on mismatch in security symbols.
3. **Production defaults file:** `sdkconfig.prod.defaults` with SB v2, FE (RELEASE after lab validation), NVS encryption or encrypted `nvs`, coredump target, CPU 240 MHz, and PSRAM only if decided (F-04-01/02/03/06/12/16).
4. **Provisioning design + scripts:** `firmware/provisioning/` with key generation (outside repo), `burn_efuses.sh` dry-run, per-device cert/key/device_id writer, and an anti-rollback security-version policy (F-04-04/05/07).
5. **NVS erase guard:** replace `main.c:97-102` unconditional erase with a guarded path, and move identity out of NVS (F-04-07).
6. **Hygiene pass:** update `.gitignore` (`build/`, `.pio/`, `sdkconfig.*`, `*.pem`, `*.key`, `*.crt`); delete the three `build_flags` lines (F-04-09, F-04-18).
7. **REQUIRES cleanup:** trim `bt`, `mbedtls`, `esp_pm`, `esp_event` until used; list `esp_random`, `esp_sleep` explicitly; add `esp_adc`/`mqtt` with their features (F-04-12).
8. **Doc truthfulness pass:** reword README/SECURITY_SPEC claims that the config does not yet back (F-04-01, F-04-06, F-04-14, F-04-20).
