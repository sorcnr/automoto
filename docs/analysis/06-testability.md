# 06 - Testability, Simulation Fidelity & Docs Consistency

## Summary

- **Zero automated tests exist.** No unit, integration, HIL, pytest-embedded, or CI config anywhere in the repo (no `.github/`, no `test/`, no `conftest.py`, no `pytest.ini`). [VERIFIED: repo file listing; `git ls-files` in base commit]
- **Simulation does not exercise the safety logic.** The Renode platform (`sim/renode/automoto.repl`) models only two UARTs and RAM/flash. It has no GPIO, I2C, RTC/TWDT, or interrupt matrix, so every `gpio_*` call in firmware goes nowhere. The Wokwi diagram models LEDs/relays/buttons only, with no modem and no LIS3DH. [VERIFIED: repl:8-31; diagram.json:5-95]
- **The mock modem is structurally incapable of testing GNSS or registration logic in firmware.** Firmware sends zero AT commands and parses zero responses. [VERIFIED: grep for `modem_send_at` callers = none; modem.c:72-76]
- **The mocks leak into shipping code paths.** `modem_get_gnss_fix()` returns hard-coded Izmir coordinates with `gps_fixed=true` and `speed=0` (modem.c:86-90); `sensors_imu_read_accel()` returns constant `z=1000` (sensors_imu.c:37-39). No build flag or runtime gate separates mock from production.
- **The safety logic is not host-testable without refactoring.** The crank interlock lives inside a FreeRTOS task loop with static state (actuator_safety.c:11-16, 36-114). Soft-kill is likewise a task (failsafe.c:12-47). No vtable, DI, or weak-symbol seam exists.
- **Docs drift is significant.** Of the 9 claims checked, 7 are DISAGREE or ABSENT (Secure Boot v2, OTA self-tests, <100 µA sleep, BLE token verification, MQTT contract, 3-stage soft-kill, 8 MB PSRAM use). Plus 13 further intra-doc and sim-doc drifts (D-08..D-20, §7).
- **Two latent P0s**: the BLE path sets ignition directly and bypasses the soft-kill lockout (ble_keyless.c:52 vs failsafe.c:33-36), and the speed gate that soft-kill stage 3 needs has no real input and would be permanently satisfied by the mock.

---

## Scope & Method

**Files read (in worktree `T6-testability`, base `0c399ed`):**
- `sim/README.md`, `sim/renode/automoto.repl`, `sim/renode/automoto.resc`, `sim/wokwi/diagram.json`, `sim/tools/mock_sim808.py`, `sim/run_renode.sh`
- `firmware/platformio.ini`, `firmware/sdkconfig.defaults`, `firmware/partitions.csv`, `firmware/CMakeLists.txt`, `firmware/main/CMakeLists.txt`, `firmware/README.md`, `firmware/SECURITY_SPECIFICATION.md`
- `firmware/main/*.c|*.h` (all 18 files)
- `PROJECT.md`, `README.md`, `docs/TARGET_MARKET_AND_USE_CASES.md`, `hardware/pcb/PCB_SPECIFICATION.md` (pin table only), `hardware/production/automoto_bom_jlcpcb.csv` (PSRAM line only)

**Commands run (read-only / scratch only):**
- `~/.local/bin/renode --version` → `Renode v1.17.0`, .NET 8.0.12 [VERIFIED]
- Renode smoke scripts in `/tmp/opencode/t6/` (outside the worktree): machine creation with `cpuType: "esp32s3"`; loading `sim/renode/automoto.repl`; running `automoto.resc` from repo root and from `/tmp`; `LoadELF` of the README path; start with no image.
- Python import of `sim/tools/mock_sim808.py` with `PYTHONDONTWRITEBYTECODE=1`, calling `handle_command` directly (no socket).
- `grep` over `firmware/` for call sites of every public function.

**Not done / could not verify:**
- No ESP-IDF, no PlatformIO, no `idf.py`, no Xtensa cross-toolchain → **no firmware build, no compile, no flash, no run of firmware in any simulator** is claimed here.
- No ESP-IDF-built ELF exists → the full Renode boot path (`start` with firmware) was not exercised. Only "machine starts, CPU aborts at 0x50000000 with no image" was observed.
- No Espressif TRM access → memory-map and UART0/USB claims are [UNVERIFIED].
- No Wokwi run (requires the Wokwi extension and a built ELF).

---

## 1. Renode ESP32-S3 Support (Q3) — verdict: PARTIAL, not proven for this firmware

**Verified facts:**
- Renode 1.17.0 installed; `renode --version` OK. [VERIFIED]
- `CPU.Xtensa` accepts `cpuType: "esp32s3"` and instantiates without error. [VERIFIED: smoke test, `sim/renode/automoto.repl:19-21` uses the same construct]
- `Infrastructure.dll` contains type/name strings `ESP32S3`, `esp32s3`, `ESP32_UART`, `ESP32_USBSerialJTAG`, `ESP32_TIMG`, `ESP32_RTC_CNTL`, `ESP32_SPIController`, `ESP32S3_EXTMEM`. [VERIFIED: `grep -a` on `~/.local/share/renode/Infrastructure.dll`; presence of a string is weak evidence]
- `UART.ESP32_UART` type resolves when instantiated. [VERIFIED: smoke4 loaded it at `0x60010000`]
- **No ESP32 platform file exists** under `platforms/cpus`, `platforms/boards`, `scripts`, or `tests` (only `platforms/cpus/xtensa-sample-controller.repl` and an Xtensa sample-controller robot test). [VERIFIED: `find`/`grep` in `~/.local/share/renode`]
- `GPIO.ESP32_GPIO` and `GPIO.Nonexistent` both fail with `Could not resolve type` → **no ESP32-S3 GPIO model is addressable by that name**. [VERIFIED: smoke2/smoke3]
- A machine with no image starts, then aborts: `CPU abort [PC=0x50000000]: Trying to execute code outside RAM or ROM`. [VERIFIED: smoke4] → the S3 reset vector / boot ROM is not modeled by this repl.

**Consequences:**
- `automoto.repl:28` and `:31` declare both UARTs as `UART.PL011` (ARM PrimeCell). The firmware drives ESP32-S3 UART registers through ESP-IDF's `driver/uart.h` (modem.c:4, 32-38). Renode *does* ship `UART.ESP32_UART`, which is the correct model. [VERIFIED for the type existing; register mismatch INFERRED]
- Nothing in the repl models GPIO, I2C (sensors_imu.c:15-27), RTC/TWDT (actuator_safety.c:23), timers (ble_keyless.c:27, esp_timer), or the interrupt matrix. So `board_*` (board_pins.c:65-96) and the actuator task cannot be exercised by Renode as written. [VERIFIED: repl has 31 lines, only memories/CPU/2 UARTs]
- The repl's memory map (`instram0 @ 0x40000000 size 0x80000`, repl:8-9; `dataram0 @ 0x3FC88000`, repl:11-12) is not checked against the S3 TRM. On the S3 the `0x40000000` region is the internal ROM, and IRAM sits elsewhere. [UNVERIFIED: needs ESP32-S3 TRM address map; treat repl:8-9 as suspect]

**What would prove or disprove support (ordered, cheapest first):**
1. `renode --version` (done) and `peripherals` after loading the repl (done: lists only the 2 UARTs, memories, cpu).
2. **10-line smoke test (not run):** a hand-assembled Xtensa snippet (or an IDF-built hello) that writes `H` to UART1 THR at `0x60010000` with ESP32_UART, and asserts the analyzer receives `H`. Requires a toolchain to build the snippet → [UNVERIFIED until run].
3. Identify the GPIO model: `ls ~/.local/share/renode/platforms/**` returned none for esp32; `strings Infrastructure.dll | grep -i gpio` to find the real GPIO type for S3 → [UNVERIFIED].
4. Only then: load a real `automoto_firmware.elf` and check for log line `Starting Safety & Keyless Task on Core 0...` (main.c:23).

---

## 2. ELF Path Mismatch (Q2) — verdict: INCONSISTENT, three different paths

- `sim/README.md:48`: `sysbus LoadELF @firmware/.pio/build/esp32s3/firmware.elf` — uses env name `esp32s3`.
- `firmware/platformio.ini:8`: `default_envs = esp32s3_automoto`; only env defined is `[env:esp32s3_automoto]` (ini:11). PlatformIO writes outputs to `.pio/build/<env-name>/`, so the matching path is `firmware/.pio/build/esp32s3_automoto/firmware.elf`. [INFERRED from PlatformIO convention; not run]
- `firmware/CMakeLists.txt:4`: `project(automoto_firmware)` → an ESP-IDF build produces `firmware/build/automoto_firmware.elf`, not `firmware.elf`. [INFERRED from IDF convention; not run]

**Trace:** The README path is wrong on two counts (env name, and `firmware.elf` vs `automoto_firmware.elf` if built with idf.py). The `firmware/` prefix is also repo-root-relative, which only works if Renode is started from the repo root (see below). I confirmed `sysbus LoadELF @firmware/.pio/build/esp32s3/firmware.elf` fails when the file is absent (expected; nothing is built) [VERIFIED: failure message in smoke run]. The README path cannot be used even after a successful PlatformIO build.

**Compounding defect - CWD-relative `.resc`:** `sim/renode/automoto.resc:9` uses `machine LoadPlatformDescription @sim/renode/automoto.repl`, which resolves against the working directory. Run from repo root it loads [VERIFIED: "AutoMoto v4.0 ... Platform Loaded" printed]. Run from `/tmp` with the absolute path to the `.resc` it fails: `Could not find file 'sim/renode/automoto.repl'` [VERIFIED]. `sim/run_renode.sh:9,20` passes the absolute `RESC_FILE` but does not `cd` to root, so the launcher breaks whenever it is not invoked from root.

---

## 3. mock_sim808.py vs firmware (Q4)

**What the firmware sends:** Nothing. `modem_send_at()` is defined (modem.c:63-80) and declared (modem.h:28) but has **zero callers** [VERIFIED: grep]. No `AT` string literal exists in `firmware/`. `modem_init()` only configures UART1 at 115200 8N1 with TX=17, RX=18 (modem.c:10-11, 23-38) and power-cycles the module if STATUS is low (modem.c:41-44).

**What the firmware parses:** Nothing. Even the one reader returns success on any bytes: `if (len > 0) { ... return ESP_OK; }` (modem.c:73-76). There is no `OK`/`ERROR`/`+CREG` matching. Therefore **the firmware does not parse any response**, and a modem replying `ERROR` is reported as success.

**Mock AT coverage (sim/tools/mock_sim808.py:58-103):**

| AT command | Mock reply | Used by firmware? |
|---|---|---|
| `AT` | `OK` (mock:58-59) | No |
| `ATE*` | `OK` (mock:61-62) | No |
| `AT+CPIN?` | `+CPIN: READY` (mock:64-65) | No |
| `AT+CSQ` | `+CSQ: 26,0` (mock:67-68) | No |
| `AT+CREG?` / `AT+CGREG?` | registered (mock:70-76) | No |
| `AT+CGNSPWR=1/0/?` | state (mock:78-86) | No |
| `AT+CGNSINF` | synthetic 21-field line (mock:35-47, 88-89) | No |
| `AT+CBC` | `+CBC: 0,95,3860` (mock:91-92) | No |
| `AT+SAPBR*`, `AT+CIPSHUT`, `AT+CIPSTATUS` (mock:94-99) | `OK` / static | No |
| **anything else** (mock:100-102) | **`OK`** | — |

**Is AT+CGNSINF realistic?** The field count is 21 (mock:42-46 emits 21 comma-separated fields; verified by parsing the generated line). Field order matches the SIM808 layout documented in mock's own comment (mock:41) [UNVERIFIED against SIMCom AT manual; no manual in repo]. Values are static: lat/lon fixed (mock:28-29), speed fixed 0.0 (mock:31), heading fixed 180.0 (mock:32), satellites fixed 12 (mock:33). The README's "Dinamik GPS … Gerçekçi GNSS uydu kilitlenmesi, hız ve koordinat" (sim/README.md:14-16, 66) overstates this. There is no motion model and no NMEA output, despite `sim/README.md:16` claiming NMEA.

**Dangerous default:** Any unhandled command (e.g. `AT+CIPSTART`, `AT+CIPSEND`, `AT+CMGS`, `AT+QMTOPEN`) gets `OK` (mock:100-102). A future MQTT/TCP driver would see a successful socket open and a successful send with no data path behind it. This is silent false-positive territory.

**Consequence for GNSS/registration testability:** Since the firmware never sends `AT+CGNSINF`, `AT+CREG?`, or `AT+CPIN?`, **the mock tests nothing in the current firmware for GNSS or registration.** It would only become useful once a parser exists, and the mock's default-OK fallback would then hide missing-command bugs. The mock also has no fault knobs (`AT+CREG?` always 1, `rssi` always 26, `gps` always fine; mock:22-25) and no way to inject `ERROR`, timeouts, or URCs.

**Other mock notes:** `pty_mode` parameter (mock:15-18) is never exposed to argparse (mock:137-141), despite the docstring's "PTY" claim (mock:4). `AT+CIPSTATUS` returns `OK` before `STATE:` (mock:99), the reverse of the real order [UNVERIFIED].

---

## 4. Simulation Fidelity — Findings Against Real Firmware

| # | Item | Simulation says | Firmware / PCB says | Verdict |
|---|---|---|---|---|
| S1 | UART1 TX/RX pins | GPIO 17/18 (repl:30) | `PIN_MODEM_TX 17`, `PIN_MODEM_RX 18` (board_pins.h:41-42); PCB Pin 10/11 IO17/IO18 (PCB_SPECIFICATION.md:157-158) | AGREE (but repl binds no pins; comment-only) |
| S2 | UART1 baud | not configured in repl | `MODEM_BAUD_RATE 115200` (modem.c:11) | ABSENT in sim |
| S3 | UART1 peripheral model | `UART.PL011` (repl:31) | ESP-IDF `driver/uart.h` on ESP32-S3 (modem.c:4, 32-38); Renode ships `ESP32_UART` (verified) | DISAGREE [INFERRED register mismatch] |
| S4 | UART0 | "USB Serial JTAG / Debug Console (GPIO 19/20)" as `UART.PL011` at 0x60000000 (repl:27-28) | PCB: IO19/IO20 = USB D-/D+ (PCB_SPECIFICATION.md:160); USB-Serial-JTAG is a separate block from UART0 [UNVERIFIED without TRM] | DISAGREE (conflation) |
| S5 | Modem TCP bridge | `CreateServerSocketTerminal 4321` on uart1 (resc:13-14); mock connects to 127.0.0.1:4321 (mock:15-17, 112-113) | README (sim/README.md:14, 56) | AGREE |
| S6 | Modem STATUS (IO21) | not modeled in repl or Wokwi | input, **internal pull-up enabled** (board_pins.c:49-52); PCB Pin 23 (PCB_SPECIFICATION.md:168) | ABSENT in sim; firmware semantics see F-06-06 |
| S7 | Modem PWRKEY (IO38) | not modeled | output (board_pins.c:18); PCB Pin 31 (PCB_SPECIFICATION.md:172) | ABSENT |
| S8 | Neutral input (IO12) | Wokwi pushbutton on GPIO 12 (diagram.json:63-68, 91-92) | active LOW (board_pins.c:95-96); pull-up (board_pins.c:51) | AGREE |
| S9 | Ignition PROFET (IO8) | Wokwi relay "IN" on GPIO 8 (diagram.json:86) | board_pins.h:23 | AGREE |
| S10 | Starter SSR (IO9) | Wokwi on GPIO 9 (diagram.json:87) | board_pins.h:24 | AGREE |
| S11 | Kill SSR (IO3) | Wokwi on GPIO 3 (diagram.json:88) | board_pins.h:22 | AGREE |
| S12 | Siren (IO11) | Wokwi buzzer on GPIO 11 (diagram.json:89) | board_pins.h:29 | AGREE |
| S13 | LEDs IO46/47/48 | diagram.json:80-86 | board_pins.h:47-49 | AGREE |
| S14 | IMU INT1 (IO4) | Wokwi pushbutton on GPIO 4 (diagram.json:93) | board_pins.h:33; read as GPIO (sensors_imu.c:40) | AGREE for pin; but see F-06-03 |
| S15 | I2C (IO1/IO2) to LIS3DH | **not modeled** | board_pins.h:18-19; sensors_imu.c:10-32 | ABSENT |
| S16 | PROFET DEN (IO15) / IS (IO10) | not modeled | board_pins.h:25-26; board_pins.c:40, 68 | ABSENT |
| S17 | Hard-limit crank 1.5 s | not simulated (no time model) | actuator_safety.h:12 | ABSENT |
| S18 | TWDT 3 s | not simulated | sdkconfig.defaults:53-58 | ABSENT |
| S19 | CAN (IO6/IO7) | README claims vcan0 (sim/README.md:19-22) | no CAN code in firmware (board_pins.h:37-38 only) | ABSENT (README describes a non-existent harness) |
| S20 | Wokwi `wokwi.toml` / ELF reference | `diagram.json` only | none in repo [VERIFIED: file listing] | ABSENT (Wokwi cannot run without it [UNVERIFIED Wokwi requirement]) |

**Renode-specific fidelity findings**
- **F-06-04 (P1):** The repl is a PL011-based UART with no peripherals for the safety logic. The README says it "birebir uygundur" with the v4.0 PCB (sim/README.md:31). That is false: the repl omits GPIO, I2C, RTC/TWDT, timers, IO-MUX, and the S3 boot ROM. Evidence: repl:1-31; smoke tests above.
- **Renode uart0 comment:** "(GPIO 19/20)" (repl:27) vs ESP32-S3 UART0 default pins (not in repo) [UNVERIFIED].

**Wokwi-specific findings**
- Wokwi models no modem: GSM LED GPIO46 is driven by `modem_is_alive()` (main.c:51-54), which reads the internally-pulled-up STATUS pin (modem.c:58-61; board_pins.c:49-52). Floating/no-modem reads HIGH → "alive" → **GSM LED lights with no modem**. The simulation therefore falsely reports a connected modem. (See F-06-06.)
- Wokwi has no LIS3DH, so motion is simulated only by a button on GPIO4 (diagram.json:70-75, 93). This matches the firmware's actual (GPIO-only) motion source (sensors_imu.c:40), but it means the I2C path is untested and possibly dead code.

---

## 5. Mock Leakage (Q5, Q6)

### 5a. `modem_get_gnss_fix()` — hard-coded Izmir fix

- Code: `modem.c:82-91` sets `latitude=38.4237`, `longitude=27.1428`, `speed_kmh=0.0f`, `satellites=9`, `gps_fixed=true`, unconditionally, and returns `ESP_OK`. The comment at modem.c:85 says "Varsayılan mock koordinatları (İzmir / Test)".
- Only caller: `main.c:59` (logs the value at main.c:60-64). No other consumer. [VERIFIED: grep]
- **Three different Izmir coordinate sets in the repo:** `modem.c:86-87` (38.4237/27.1428), `mock_sim808.py:28-29` (38.4332/27.1408), `PROJECT.md:119-120` (38.4237/27.1428 as a telemetry example). [VERIFIED]

**Blast radius if it ships:**
- Today: fake location is logged (main.c:60-61) and no MQTT publish exists, so it is not transmitted. Blast radius is low **now**.
- Latent: the spec's soft-kill stage 3 requires `V = 0 km/h` confirmed by "LIS3DH ivmeölçer ve GPS" (SECURITY_SPECIFICATION.md:138; PROJECT.md:24; TARGET_MARKET_AND_USE_CASES.md:154) and remote kill is held until speed = 0 (PROJECT.md:159). With `speed_kmh=0.0f` hard-coded (modem.c:88), **any speed gate evaluates "stopped" permanently**. A kill/lockout would then fire at full speed → rear-wheel lock and crash risk, which is the exact hazard the spec exists to prevent (SECURITY_SPECIFICATION.md:134; TARGET:82). **P0 latent.**
- `gps_fixed=true` (modem.c:90) would defeat any "no fix → refuse remote start" gate and the geofence feature (PROJECT.md:25; TARGET_MARKET_AND_USE_CASES.md:63).

**Recommended gating (concrete):**
1. **Build-time (primary):** wrap the mock in `#if defined(AUTOMOTO_SIM_MOCKS)` in `modem.c` and `sensors_imu.c`. Define the macro only in a new `[env:sim]` section in `platformio.ini` (new, not in repo today) and in a `CONFIG_AUTOMOTO_SIM_MOCKS` Kconfig symbol set only in a `sdkconfig.sim` overlay. Production build compiles `modem_get_gnss_fix()` to return `ESP_ERR_NOT_SUPPORTED` / `gps_fixed=false` when the macro is absent. Add `#if defined(AUTOMOTO_SIM_MOCKS) && defined(AUTOMOTO_RELEASE) #error` in a new `build_guard.h` included by `main.c`.
2. **Runtime fault (defence in depth):** in `app_main` (main.c:88+), check a Kconfig/NVS flag `sim_mocks_active`; if set and the build is flagged as release (e.g. secure-boot enabled), call `esp_restart()` or refuse to enter `safety_core0_task`. Log at ERROR.
3. **CI gate:** `nm`/`strings` on the release ELF must not contain `38.4237` or the mock marker. Fail the build if found. (No CI exists yet; see §7.)
4. **Data-level:** make `gnss_telemetry_t.gps_fixed` default `false` and require a real AT parse before setting `true`.

### 5b. `sensors_imu_read_accel()` — constant `z=1000`

- Code: `sensors_imu.c:34-42` sets `x=0, y=0, z=1000` and returns `ESP_OK`. `motion_detected` comes from `gpio_get_level(PIN_IMU_INT1)` (sensors_imu.c:40), not from the LIS3DH.
- **`sensors_imu_init()` never talks to the LIS3DH** (sensors_imu.c:10-32): no `WHO_AM_I` check, no `CTRL_REG` write, no `i2c_master_*` transaction. It only installs the I2C driver. `sensors_imu_configure_wakeup_threshold()` is a log-only stub (sensors_imu.c:44-47). [VERIFIED]
- Consumers of `x,y,z`: none in firmware. Only `motion_detected` is used (main.c:28-34).

**Silent degradation:**
- Any tilt, lift, or fall detection built on `x,y,z` (PROJECT.md:14 "sehpaya alınması, dik konuma getirilmesi… anlık donanımsal kesme"; TARGET:38 "dik konuma getirilme veya kaldırılma") would see a constant upright 1 g and **never trigger**. `sensors_imu_read_accel()` returns `ESP_OK` (sensors_imu.c:41), so no error surfaces. **Theft-enabling if such logic is added without a real driver.**
- The **motion path reads GPIO4 without configuring it**: `board_pins_init()` configures only IO3/8/9/15/11/17?/46/47/48 outputs and IO12/IO21 inputs (board_pins.c:12-21, 47-49). `PIN_IMU_INT1` (GPIO4) is never configured as input. A floating GPIO4 can read 1 (false alarm) or 0 (missed motion). [VERIFIED: config masks]
- **Motion is not wired to any actuator:** `main.c:28-34` only toggles the alarm LED (GPIO47). The siren is only driven by soft-kill stage 2 (failsafe.c:29), which has no caller. So a real motion event produces **no siren and no kill**. PROJECT.md:82 says "sireni çalar" (sounds the siren) [DISAGREE, see §8].

**Fix sketch:** real LIS3DH driver (WHO_AM_I=0x33 check, CTRL_REG setup, INT1 latched, configure GPIO4 as input with pull-down); fail-closed `ESP_ERR_NOT_FOUND` on WHO_AM_I mismatch; gate the production build as in 5a.

### 5c. Test seams (Q6) — verdict: NONE

- **No HAL vtable.** `board_pins.h` exposes free functions (board_pins.h:52-57); callers invoke them directly.
- **No weak symbols** anywhere in `firmware/` [VERIFIED: grep `__attribute__|weak` = none].
- **No dependency injection.** Modules use file-scope statics: `actuator_safety.c:11-16`, `failsafe.c:9-10`, `ble_keyless.c:9`, `modem.c:14`.
- **Link-time substitution is partially possible:** `actuator_safety.c` calls `board_set_*` / `board_is_neutral` as external symbols (actuator_safety.c:40-44, 55, 66-109) and `failsafe.c` calls `board_set_*` (failsafe.c:20-36, 76-77, 92). So a host `board_fake.c` could replace `board_pins.c` at link time, **without editing those modules**. This is the cheapest seam.
- **But** the logic is not callable on its own: the interlock decision sits inside `actuator_safety_task`'s `while(1)` (actuator_safety.c:31-115) that also calls `xQueueReceive`, `esp_task_wdt_reset`, and `esp_task_wdt_add` (actuator_safety.c:23, 33, 36). Soft-kill logic is inside `soft_kill_worker_task` (failsafe.c:12-47) with `vTaskDelay` and a `while` on a volatile state. Both need FreeRTOS, `esp_log`, `esp_task_wdt`, and `esp_timer` headers on the host.
- **Surgery estimate:**
  - *Option A (no source change):* write host shims for `freertos/*.h`, `esp_task_wdt.h`, `esp_log.h`, `esp_timer.h`, plus a `board_fake.c`, and run the task in a thread with a fake queue. Probably 300–400 LOC of shims; fragile timing; tests the scheduler more than the logic. Not recommended.
  - *Option B (recommended, ~1–2 days):* extract pure functions, no FreeRTOS in the decision path:
    - `crank_decide(ignition_on, neutral, duration_ms) -> {ACCEPT(ms) | REJECT_IGNITION | REJECT_GEAR}` from actuator_safety.c:48-68.
    - `crank_tick(state*, neutral, elapsed_us) -> {KEEP | ABORT_GEAR | ABORT_TIMEOUT}` from actuator_safety.c:98-114, using **`elapsed_us` from a passed-in clock**, not loop count (see F-06-08).
    - `softkill_next(state*, speed_kmh, stage_elapsed_us) -> stage` from failsafe.c:16-35.
    - Task files become thin adapters. Host tests use Unity/CMock against the pure functions with a fake clock.
  - *Option C:* an `automoto_hal.h` vtable `{ set_ignition, set_starter, set_kill, set_siren, is_neutral, now_us }` injected at `actuator_safety_init()` and `failsafe_init()`. Larger change (touches every caller); best long-term.

---

## 6. Test Inventory (Q7) — verdict: ZERO automated tests

Evidence:
- No `.github/` directory in repo root or worktree. [VERIFIED: `ls -la`]
- No `test/` dir, no `conftest.py`, `pytest.ini`, `tox.ini`, `Makefile`, `*.robot` in repo. [VERIFIED: `find` for test/CI patterns returned nothing]
- `firmware/platformio.ini` has no `test_dir`, no `[env:native]`, no `test_framework` (ini:1-35). [VERIFIED]
- `firmware/CMakeLists.txt:1-7` and `firmware/main/CMakeLists.txt:1-26`: no `test/` component and no `idf_component_register(... REQUIRES unity)`. [VERIFIED]
- `sim/` has no test scripts; `sim/README.md` contains no test instructions. [VERIFIED]
- `docs/` has no test guide, although `PROJECT.md:189` says `docs/` contains "test kılavuzları" (test guides) and `docs/` contains only `TARGET_MARKET_AND_USE_CASES.md`. [VERIFIED: `ls docs`] → **D-19 drift**.
- Phase checklist: all phases unchecked (PROJECT.md:195-200), so no test gate is claimed as done.
- `.gitignore` does not exclude `firmware/.pio/` or `firmware/build/` (`.gitignore:1-21`). Build outputs could be committed. [VERIFIED]

---

## 7. Docs Consistency Table (Q8)

Each row: doc quote, code quote, verdict. Line refs are `path:line`.

| # | Claim | Doc quote | Code quote | Verdict |
|---|---|---|---|---|
| 1 | TWDT-protected actuators | `firmware/README.md:36-38`: "Marş rölesi… kontak PROFET'i… Soft-Cut SSR'si… genel ağ… izole edilmiştir… Görev her 20 ms'de bir `esp_task_wdt_reset()` ile beslenir." | `actuator_safety.c:23` `esp_task_wdt_add(NULL)`; `:33` `esp_task_wdt_reset()`; `sdkconfig.defaults:18-23` TWDT enabled, 3 s, panic | **AGREE** (scoped to actuator task only). Caveats: (a) the watchdog is fed in the same loop as the logic (actuator_safety.c:33 precedes the logic), so it detects starvation, not wrong decisions; (b) "tüm röleleri 0 seviyesine çeker" (firmware/README.md:38) is [UNVERIFIED] — no panic handler touches GPIO. |
| 2 | Secure Boot v2 | `SECURITY_SPECIFICATION.md:29` "Secure Boot v2 (RSA-3072)"; `firmware/README.md:41-43` "RSA-3072 imzalı Secure Boot v2 bootloader'ı için…"; `partitions.csv:97` "Secure Boot v2, Flash Encryption ve OTA Rollback Uyumlu" | `sdkconfig.defaults:15` `CONFIG_SECURE_BOOT_SUPPORTS_PLAINTEXT_BOOTLOADER=y`. No `CONFIG_SECURE_BOOT=y`, no `CONFIG_SECURE_FLASH_ENC_ENABLED`, no signing key config anywhere (grep). | **ABSENT** (enablement). The one flag present is a "supports plaintext" option, not enablement [UNVERIFIED exact IDF semantics]. Partition `encrypted` flags (partitions.csv:12, 15) are inert without flash encryption. |
| 3 | OTA rollback with hardware self-tests | `firmware/README.md:47-48`: "Yeni sürüm tüm donanım testlerini (GPIO, IMU, Modem, Aktüatörler) başarıyla tamamlayıp `esp_ota_mark_app_valid_cancel_rollback()` çağırmadan çöker…" | `main.c:125-128`: `modem_init()` then `verify_and_confirm_ota_rollback()`. `main.c:81` marks valid unconditionally on `PENDING_VERIFY`. `modem.c:41-44` ignores `modem_is_alive()` result after power cycle. `sensors_imu.c:10-32` has no device check. | **DISAGREE.** Rollback mechanics present (`sdkconfig.defaults:13`, `main.c:74-81`). Self-tests absent: confirmation happens after init with no GPIO/IMU/modem/actuator check. |
| 4 | <100 µA deep sleep | `PROJECT.md:77`: "Akım çekişi uykudayken 100 µA seviyesinin altındadır." `TARGET_MARKET_AND_USE_CASES.md:36`: "Uykuda <100 µA" | `power_manager.c:32-51` defines `power_manager_enter_deep_sleep()`; **no caller** [VERIFIED grep]. No RTC GPIO hold, no current budget, no measurement. `sdkconfig.defaults:43` only `ESP_SLEEP_POWER_DOWN_FLASH`. | **ABSENT** (no sleep entered, no measurement; untestable in sim). |
| 5 | BLE challenge-response | `SECURITY_SPECIFICATION.md:52-57`: 16-byte nonce via GATT; `Token = AES-128-GCM(Nonce‖Timestamp, Device_Secret)`; ±5 s replay window. `SECURITY_SPECIFICATION.md:62`: "Δt > 18 ms … kontak açılmaz". | `ble_keyless.h:12` `BLE_MAX_ALLOWED_RTT_US 18000` (**AGREE with 18 ms**); `ble_keyless.c:26` nonce generated, **never transmitted**; `:31` `response`/`len` parameters **never read**; `:39` RTT uses caller-supplied `received_timestamp_us`; `:49` comment "Kriptografik İmza / Token Teyidi" with **no code** below it; `:52` `board_set_ignition(true)` on success. | **DISAGREE.** RTT threshold matches, but the token/AES-GCM/replay check is absent; nonce is not sent; receive time is caller-supplied, so the RTT check is spoofable by the caller. F-06-01 and F-06-12. |
| 6 | MQTT topic contract | `PROJECT.md:87-104`: topics `automoto/{device_id}/telemetry|events|commands|response|status`, `status` QoS 1 retained (`:104`). `SECURITY_SPECIFICATION.md:83-91`: publish telemetry/events/response; subscribe commands only; no wildcards. | No MQTT client in firmware. Only mention: `main.c:43` comment. No `esp_mqtt`, no `mqtt_client` in `CMakeLists.txt:12-22` or `main/CMakeLists.txt:14-25`. | **ABSENT.** |
| 7 | 3-stage soft-kill | `SECURITY_SPECIFICATION.md:134-138`: Stage 1 pulses at <20 km/h scale; Stage 2 siren when `<20 km/h`; Stage 3 at `V = 0 km/h` (LIS3DH + GPS). `PROJECT.md:24`: "hız 20 km/h altına çekilir". | `failsafe.c:19-24` fixed 100 × (15+15 ms) = 3 s pulse loop, **no speed input**; `:27-30` siren after fixed loop, 2 s; `:33-36` ignition off after fixed timeline. No speed/`V` parameter anywhere. `failsafe_trigger_soft_kill()` (failsafe.c:55) has **no caller**. | **DISAGREE.** Stage ordering present, but transitions are timer-based, not speed-based. The trigger is unreachable. F-06-13. |
| 8 | Neutral interlock | `PROJECT.md:158`: "Araç vitesteyken uzaktan marş komutu gelse dahi marş motoruna asla enerji verilmez." `SECURITY_SPECIFICATION.md:140`: "Motosiklet vitesteyken marş motoruna kesinlikle enerji iletilmez." | `actuator_safety.c:55-58` reject crank in gear; `:100-104` abort mid-crank on neutral loss; `board_pins.c:75-79` second check in `board_set_starter`; `board_pins.c:95-96` active-LOW read. **`actuator_request_crank()` (actuator_safety.c:168) has no caller**, so the crank path is unreachable. The series-hardware half is not in code; PCB_SPECIFICATION.md:167 shows only sensing. | **AGREE** (software logic correct in intent, and triple-guarded), but **unreachable** today and the hardware series path is [UNVERIFIED]. Doc says "donanımsal veya mantıksal" (hardware or logical) — logical half exists. |
| 9 | 8 MB PSRAM | `PCB_SPECIFICATION.md:88`: "16MB Flash, 8MB PSRAM"; `platformio.ini:3,16`: "8MB Octal PSRAM", "8MB Octal OPI PSRAM"; `hardware/production/automoto_bom_jlcpcb.csv:2` "8MB PSRAM". | `sdkconfig.defaults`: no `CONFIG_SPIRAM*`, no `CONFIG_ESPTOOLPY_OCT*`; `sdkconfig.defaults:35` `CONFIG_BT_NIMBLE_MEM_ALLOC_MODE_INTERNAL=y` (internal RAM only). No `MALLOC_CAP_SPIRAM` anywhere. | **ABSENT in firmware.** Hardware docs agree on the part (N16R8). The firmware neither enables nor uses PSRAM, and PlatformIO's `board = esp32-s3-devkitc-1` (ini:14) with only `flash_size` overridden (ini:17) does not enable octal PSRAM. |

**Summary: 2 AGREE (row 1 scoped to the actuator task; row 8 unreachable in code), 7 DISAGREE/ABSENT (rows 2, 3, 4, 5, 6, 7, 9).**

### Extra doc-internal and doc-code drift (D-08 … D-20)

| ID | Drift | Evidence |
|---|---|---|
| D-08 | Renode repl claims PCB-exact fidelity | `sim/README.md:31` vs repl:1-31 |
| D-09 | "Dinamik GPS / NMEA" overclaim | `sim/README.md:14-16, 66` vs `mock_sim808.py:28-33`, no NMEA emitter |
| D-10 | CSQ example drift | `sim/README.md:64` "+CSQ: 28,0" vs `mock_sim808.py:25,68` (26) |
| D-11 | Launch command requires repo-root CWD | `sim/README.md:37,41` vs `automoto.resc:9`; `run_renode.sh:20` |
| D-12 | ELF path | `sim/README.md:48` vs `platformio.ini:8`, `CMakeLists.txt:4` (see §2) |
| D-13 | CAN harness claimed | `sim/README.md:19-22` (vcan0) vs no CAN code (`board_pins.h:37-38` only) |
| D-14 | Izmir coordinates in three versions | `modem.c:86-87`, `mock_sim808.py:28-29`, `PROJECT.md:119-120` |
| D-15 | Remote-start/telemetry cadence: 1.5 s vs 500 ms | `PROJECT.md:80` "her 1.5 saniyede bir" vs `main.c:39` `vTaskDelay(500)`; BLE scan is a stub `ble_keyless.c:20-29` |
| D-16 | Wake-source pin assignment contradicts itself | `PROJECT.md:81` modem RI → EXT0; `PROJECT.md:82` IMU → EXT1; code `power_manager.c:20-25` EXT0=IMU, EXT1=modem; `:43` IMU on EXT0. No RI pin defined in `board_pins.h`. |
| D-17 | Command schema disagrees across the two docs | `PROJECT.md:133-146` (`token`, `params.ignition`, `starter_crank_ms`) vs `SECURITY_SPECIFICATION.md:97-107` (`signature`, `ts`, `nonce`, `params.crank_ms`). Also crank window: ±5 s (SEC:57) vs ±15 s (SEC:112) — different channels, but undocumented as such. |
| D-18 | Module vendor drift | `PROJECT.md:39,60` SIM808 vs SIM7080G in block diagram; `PROJECT.md:73` cites `AT+QMTOPEN/AT+QMTPUB` as SIMCom (these are Quectel commands) [UNVERIFIED vendor-specific syntax] |
| D-19 | Test guides promised, none exist | `PROJECT.md:189` "docs/ … test kılavuzları" vs `docs/` contains only `TARGET_MARKET_AND_USE_CASES.md` |
| D-20 | Bypass vs "isolation" claim | `firmware/README.md:36` "izole edilmiştir" vs `ble_keyless.c:52` writes PROFET directly |

*Counting note: the claims table has 9 rows (7 DISAGREE/ABSENT). Extras are D-08..D-20 (13 items). Total docs-drift count: **20** (7 table + 13 extra).*

---

## 8. Findings

### F-06-01 - BLE auth path sets ignition directly and bypasses soft-kill lockout [P0] [VERIFIED]
- **Evidence:** `ble_keyless.c:52` `board_set_ignition(true)`. Lockout set at `failsafe.c:33-36` (`board_set_ignition(false)`, `board_set_kill_ssr(true)`) and guard `failsafe.c:87-92` (`failsafe_can_crank_starter`) are never consulted by the BLE path. `ble_keyless_verify_challenge_response()` has **no caller** (grep), so the path is latent.
- **Failure mode + trigger:** Once the BLE receive path is wired (the only consumer of this function), a phone that passes the RTT check during FULL_LOCKOUT re-energizes `PROFET_IN` (GPIO8) while `SSR_KILL` (GPIO3) is held high. Two outputs fight; the ignition is re-armed on a stolen bike that the server has locked.
- **Consequence:** Theft-enabling; defeats the Stage 3 lock (SECURITY_SPECIFICATION.md:138).
- **Fix sketch:** Route `ble_keyless` through `actuator_request_ignition()` (actuator_safety.c:159) **and** check `failsafe_get_kill_state() == KILL_STATE_IDLE` in the adapter. Make `board_set_ignition` reject `true` while `current_kill_state != IDLE` (single choke point).
- **Verification:** Host unit test: enter FULL_LOCKOUT, call verify with valid RTT, assert ignition stays off and returns false.

### F-06-02 - Mock GNSS speed=0 / gps_fixed=true would defeat any speed gate [P0 latent] [VERIFIED code, INFERRED future impact]
- **Evidence:** `modem.c:88-90`; only caller `main.c:59` (log only). Spec requires speed = 0 for stage 3 (SECURITY_SPECIFICATION.md:138; PROJECT.md:159).
- **Failure mode + trigger:** The day a speed-gated kill is wired to `gnss_fix.speed_kmh`, it reads 0 at full speed, so stage 3 locks ignition on a moving bike.
- **Consequence:** Safety-of-life (rear-wheel lock, crash). P0 once wired.
- **Fix sketch:** §5a. Build-time mock gating; `gps_fixed` default false; refuse kill-by-speed when `!gps_fixed` (fail to the safe default, i.e. do not kill on unknown speed; use the IMU/timer fallback instead).
- **Verification:** Build guard (`#error`) + ELF string scan for `38.4237`; host test: `gps_fixed=false` → speed gate returns "unknown", not "stopped".

### F-06-03 - Motion path is unconfigured GPIO, no LIS3DH driver, and no siren link [P1; P0 if a consumer is added] [VERIFIED]
- **Evidence:** `sensors_imu.c:10-32` (no device I/O), `:34-42` (fixed accel, GPIO4 read), `board_pins.c:47-50` (GPIO4 not in any mask), `main.c:28-34` (LED only), `failsafe.c:29` (siren only in soft-kill, no caller), `sensors_imu.c:44-47` (stub).
- **Failure mode + trigger:** Floating GPIO4 can read 1 (false alarm) or 0 (missed motion). A real lift/tilt event produces no siren and no kill.
- **Consequence:** Theft-enabling: the documented motion alarm (PROJECT.md:82 "sireni çalar") does nothing.
- **Fix sketch:** Configure `PIN_IMU_INT1` as input with pull-down in `board_pins_init`; implement LIS3DH WHO_AM_I + CTRL_REG + latched INT; route motion to the siren via the actuator queue; fail-closed on WHO_AM_I mismatch.
- **Verification:** Host unit test with fake I2C (see §5c Option B); HIL: lift the bike, assert siren output within X ms.

### F-06-04 - Renode platform is not a usable ESP32-S3 model for this firmware [P1] [VERIFIED facts, INFERRED impact]
- **Evidence:** `automoto.repl:28,31` (`UART.PL011`); no GPIO/I2C/TWDT/RTC in repl (repl:1-31); `GPIO.ESP32_GPIO` unresolvable (smoke2/3); CPU aborts at `0x50000000` with no image (smoke4); `sim/README.md:31` overclaims PCB fidelity.
- **Failure mode + trigger:** Any test run in Renode executes `gpio_*`, `i2c_*`, `esp_task_wdt_*`, and `esp_timer` against unmodeled or absent peripherals. Results are meaningless or the machine aborts.
- **Consequence:** Simulation provides no safety evidence. Teams may believe it does (README overclaim).
- **Fix sketch:** Replace `UART.PL011` with `UART.ESP32_UART` for uart0/uart1; identify the S3 GPIO/TIMG/RTC/INTMATRIX model types from the Renode install (or add them); add an explicit reset vector; state in README that Renode is a **bring-up-only** tool until §1's smoke test passes.
- **Verification:** The 10-line smoke test in §1 (UART1 THR `H`); then `peripherals` shows GPIO; then boot a real IDF ELF to the `Starting Safety` log line.

### F-06-05 - ELF path and CWD dependence break the documented launch [P2] [VERIFIED]
- **Evidence:** `sim/README.md:48` vs `platformio.ini:8`; `CMakeLists.txt:4`; `automoto.resc:9` relative path (fails from `/tmp`, verified); `run_renode.sh:9,17,20` absolute `.resc` but relative repl.
- **Failure mode + trigger:** Following the README, or running `run_renode.sh` from any directory other than repo root, fails at `LoadPlatformDescription`, and the ELF path fails after a build.
- **Consequence:** Reproducibility/debuggability; not a product-safety issue.
- **Fix sketch:** `automoto.resc` should use `$ORIGIN`-style or `@$(dirname)` via `run_renode.sh` passing `-e "set ROOT=..."`; README ELF path → `firmware/.pio/build/esp32s3_automoto/firmware.elf` (and ESP-IDF variant).
- **Verification:** Run `renode --disable-gui -e "include @<abs>/automoto.resc"` from `/tmp` → must succeed.

### F-06-06 - Modem STATUS pin is internally pulled up, so `modem_is_alive()` is vacuous [P1] [VERIFIED code, VERIFIED sim effect]
- **Evidence:** `board_pins.c:48-52` puts `PIN_MODEM_STATUS` (GPIO21) into the input mask with `pull_up_en = ENABLE`; `modem.c:58-61` returns `gpio_get_level(STATUS)==1`; `main.c:51-56` lights GSM LED and skips power cycle when alive. Wokwi has no modem → GPIO21 floats high → GSM LED lit (sim shows a connected modem that does not exist).
- **Failure mode + trigger:** Modem absent, unpowered, or STATUS wire cut → reads HIGH → "alive" forever → no power-cycle recovery, GSM LED lies.
- **Consequence:** Reliability and false telemetry status. Also hides a dead cellular link from the user.
- **Fix sketch:** Pull-down (or none) on STATUS; require a positive AT round-trip (`AT` → `OK`) to set alive; debounce.
- **Verification:** HIL with modem unplugged → GSM LED off; sim: wokwi LED stays off.

### F-06-07 - Firmware sends no AT commands and treats any reply as success [P1] [VERIFIED]
- **Evidence:** `modem.c:63-80` (no caller, grep); `modem.c:72-76` (`len > 0` → `ESP_OK`); `mock_sim808.py:100-102` (default `OK`); no AT literal in `firmware/`.
- **Failure mode + trigger:** Any future caller of `modem_send_at("AT+CIPSTART...")` receives `ESP_OK` on an `ERROR` reply, and on a sim run the mock answers `OK` to everything not implemented.
- **Consequence:** GNSS and registration are untestable end-to-end; the sim produces false passes.
- **Fix sketch:** Match `OK`/`ERROR`/`+CME ERROR` explicitly; return `ESP_ERR_INVALID_RESPONSE` on `ERROR`; change mock default to `ERROR` for unknown commands and log unknowns.
- **Verification:** Host test (fake UART buffer) with `ERROR` → must not return `ESP_OK`.

### F-06-08 - Crank hard-limit is a loop-count timer, not wall-clock [P1] [VERIFIED code, INFERRED timing]
- **Evidence:** `actuator_safety.c:105-112` decrements `s_crank_remaining_ms` by a constant 20 per loop iteration; loop wakes early on each queue message (`:36`), so messages cause extra decrements. A stalled loop (not panicked, e.g. blocked on `esp_task_wdt_reset` contention or preempted) does not decrement → starter stays on. `firmware/README.md:39` claims "bağımsız zamanlayıcı… en geç 1500 ms içinde zorla keser" (independent timer, cut within 1500 ms).
- **Failure mode + trigger:** Queue burst (≥N commands) shortens the countdown; a delayed task extends the crank past 1.5 s.
- **Consequence:** Starter SSR overrun, battery drain, starter damage. Safety-relevant timing claim is false.
- **Fix sketch:** Use `esp_timer_get_time()` deadline (`crank_deadline_us`); check it on every loop, not per iteration. Keep TWDT feed as-is.
- **Verification:** Host test with fake clock: 10 queued no-op messages during a crank must not shorten the crank; advancing fake clock past 1500 ms must cut it.

### F-06-09 - OTA rollback confirmation has no hardware self-tests [P1] [VERIFIED]
- **Evidence:** `main.c:125-128` → `main.c:70-86` unconditional confirm; `modem.c:41-44` ignores result; `sensors_imu.c:10-32` no device check; `firmware/README.md:47-48` promises GPIO/IMU/modem/actuator tests first.
- **Failure mode + trigger:** A firmware whose modem or IMU is dead passes confirmation and stays in production.
- **Consequence:** Bricked or non-functional fleet unit; rollback never triggers.
- **Fix sketch:** Self-test function returning `ESP_OK` only if: IMU WHO_AM_I ok, modem AT `OK` within timeout, actuator queue accepts a no-op, TWDT registered. Confirm only then; otherwise `esp_ota_mark_app_invalid_rollback_and_reboot()`.
- **Verification:** HIL with modem unplugged on an OTA image → device must roll back.

### F-06-10 - Secure Boot v2 and flash encryption not enabled [P1 production blocker] [VERIFIED]
- **Evidence:** `sdkconfig.defaults:15` only; no `CONFIG_SECURE_BOOT`, no `CONFIG_SECURE_FLASH_ENC_ENABLED` (grep). `SECURITY_SPECIFICATION.md:29-30`, checklist `:153` unchecked.
- **Failure mode + trigger:** Shipping this config yields an unsigned, unencrypted image. Anyone with the flash image can read secrets and load code.
- **Consequence:** Theft-enabling (fake firmware) and key exposure.
- **Fix sketch:** Add `CONFIG_SECURE_BOOT=y`, `CONFIG_SECURE_BOOT_V2_ENABLED=y`, signing key path, and `CONFIG_SECURE_FLASH_ENC_ENABLED=y` in a `sdkconfig.production` overlay; keep dev config unsigned.
- **Verification:** After build, `espsecure.py verify_signature` passes; eFuse dump shows SB/FE bits set on a dev board only.

### F-06-11 - Deep sleep never entered; wake sources contradict docs [P2] [VERIFIED]
- **Evidence:** `power_manager.c:32-51` no caller; `PROJECT.md:77` (<100 µA); `PROJECT.md:80` (1.5 s); `PROJECT.md:81-82` (RI→EXT0, IMU→EXT1) vs `power_manager.c:20-25,43` (IMU→EXT0, modem→EXT1); no RI pin in `board_pins.h`.
- **Failure mode + trigger:** Device never sleeps → battery drains in 3–4 days (TARGET:36). Wake wiring is inverted vs spec.
- **Consequence:** Product failure; undetectable in sim.
- **Fix sketch:** Call `power_manager_enter_deep_sleep` from a scheduler; fix D-16 in docs; add RI pin; HIL current measurement.
- **Verification:** HIL µA meter in deep sleep; EXT0/EXT1 pin assignment test.

### F-06-12 - BLE challenge-response does not verify any token; RTT is spoofable [P1] [VERIFIED]
- **Evidence:** `ble_keyless.c:26` nonce unsent; `:31` `response`/`len` unused; `:39` `received_timestamp_us` supplied by caller; `:49` no check; `SECURITY_SPECIFICATION.md:52-62`.
- **Failure mode + trigger:** Any caller that passes `received_timestamp_us = sent + 1000` passes auth with arbitrary bytes.
- **Consequence:** Keyless ignition bypass (theft-enabling) once wired.
- **Fix sketch:** Timestamp captured in the BLE receive ISR/callback (not caller-supplied); implement AES-128-GCM verification (mbedtls is already REQUIRED: `main/CMakeLists.txt:20`, sdkconfig.defaults:81-84); enforce the ±5 s window; nonce via GATT.
- **Verification:** Host test: wrong token → false; correct token with 19 ms RTT → false; with 17 ms → true; replayed token → false.

### F-06-13 - Soft-kill is not speed-gated and its trigger has no caller [P1] [VERIFIED]
- **Evidence:** `failsafe.c:16-35` fixed timeline; `:55` `failsafe_trigger_soft_kill()` no caller (grep); spec `SECURITY_SPECIFICATION.md:134-138`.
- **Failure mode + trigger:** When wired, a kill at 100 km/h proceeds through fixed timers, and stage 3 ignition-off occurs regardless of speed. Also the 15 ms pulse (failsafe.c:20-23) is a 30 ms period (15 on, 15 off), not "15 ms aralıklarla" as documented [INFERRED ambiguity].
- **Consequence:** Rider injury (stage 3 at speed). Also the feature cannot be exercised.
- **Fix sketch:** Add `speed_kmh` input; stage 2→3 only when `speed < 1` (or IMU-stationary) with a timeout fallback; trigger wired from the server command path via the actuator queue; host-test the state machine (§5c).
- **Verification:** Host test: `speed=100` → never reaches stage 3 before deceleration; timeout fallback fires.

### F-06-14 - MQTT is entirely absent [P1] [VERIFIED]
- **Evidence:** No MQTT in firmware; `PROJECT.md:87-104` and `SECURITY_SPECIFICATION.md:81-91` define the contract; `PROJECT.md:198` and `:199` phases unchecked.
- **Consequence:** No remote start/kill is possible; the mock/sim cannot test the contract.
- **Fix sketch:** Implement topic constants and a JSON schema in a single header; add a host test that compares the topic strings to the spec (a doc-as-test check).
- **Verification:** A grep-based test that every topic in `PROJECT.md:87-104` appears in code.

### F-06-15 - No host-testable seam; safety logic coupled to FreeRTOS [P1] [VERIFIED]
- **Evidence:** §5c. No vtable, no weak symbols, file-scope statics (`actuator_safety.c:11-16`, `failsafe.c:9-10`), logic inside tasks (`actuator_safety.c:31-115`, `failsafe.c:12-47`).
- **Consequence:** No unit test for the interlocks; F-06-01/02/08/13 are undetectable without it.
- **Fix sketch:** §5c Option B now; Option C long-term.
- **Verification:** A host `pio test -e native` or CMake host target runs the extracted functions.

### F-06-16 - Zero automated tests and no CI [P1] [VERIFIED]
- **Evidence:** §6.
- **Consequence:** No regression signal for any safety rule. Every finding above would survive a commit.
- **Fix sketch:** §9 pyramid; minimum: host unit tests + GitHub Actions job that runs `pio test -e native` and `pio run -e esp32s3_automoto` (build only, no flash).
- **Verification:** CI green on a PR that adds a deliberately failing crank test.

### F-06-17 - Wokwi project incomplete and not reproducible [P2] [VERIFIED]
- **Evidence:** no `wokwi.toml`; `diagram.json:1-96` has no modem, I2C, or PROFET DEN/IS; `sim/README.md:71-83` describes it as a full test rig.
- **Consequence:** Interactive demo only; cannot run firmware without a manually added ELF path.
- **Fix sketch:** Add `wokwi.toml` pointing at the sim ELF; document it as a GPIO demo, not a test.
- **Verification:** Wokwi opens and runs the built ELF [UNVERIFIED; needs build + extension].

### F-06-18 - PSRAM configured in docs, unused in firmware [P2] [VERIFIED]
- **Evidence:** D-table row 9; `platformio.ini:3,16`; no SPIRAM config.
- **Consequence:** Wasted BOM capability; or if the code later assumes PSRAM, it will fail at runtime.
- **Fix sketch:** Either enable `CONFIG_SPIRAM=y` with `CONFIG_SPIRAM_MODE_OCT` (if BOM part is N16R8 with octal PSRAM), or update docs to "PSRAM not used".
- **Verification:** Boot log shows `Found 8MB PSRAM` (only on HW) [UNVERIFIED].

### F-06-19 - TWDT covers the actuator task only; panic relay-state claim unverified [P2] [VERIFIED scope / UNVERIFIED behaviour]
- **Evidence:** `actuator_safety.c:23` only; `firmware/README.md:38` "tüm röleleri 0 seviyesine çeker" with no code.
- **Consequence:** A hung soft-kill task (`failsafe.c:12-47`, not registered) or cellular task (`main.c:44-67`) is not watchdog-protected. Relay state after reset is whatever the GPIO reset default is [UNVERIFIED].
- **Fix sketch:** Register all safety-relevant tasks; add an explicit boot-time `board_pins_init` before any task (already done at main.c:105); verify reset GPIO state on HW.
- **Verification:** HIL: block the soft-kill task for >3 s → panic → measure GPIO levels.

### F-06-20 - Neutral interlock is correct in intent but unreachable and has a single-GPIO bypass [P2] [VERIFIED code / INFERRED bypass]
- **Evidence:** `actuator_safety.c:55-58, 100-104`; `board_pins.c:75-79, 95-96`; `actuator_request_crank` no caller (grep); `PCB_SPECIFICATION.md:167` single sense pin; a short of the optocoupler output to GND reads as "neutral" (board_pins.c:96 `== 0`).
- **Consequence:** Crank path cannot be exercised; hard-wire short defeats the check.
- **Fix sketch:** Require the sense line to be LOW **and** a second independent source (e.g., a current-sense or a tilt/clutch check) [INFERRED design option]; add a hardware self-test at boot that toggles the sense input expectation.
- **Verification:** HIL: short sense line to GND → crank must still be refused (currently not).

### F-06-21 - `.gitignore` misses PlatformIO and IDF build outputs [P3] [VERIFIED]
- **Evidence:** `.gitignore:1-21` has no `.pio/`, `build/`, `sdkconfig`.
- **Fix sketch:** Add `firmware/.pio/`, `firmware/build/`, `firmware/sdkconfig` (keep `sdkconfig.defaults`).

### F-06-22 - Renode uart0 identity conflated with USB-Serial-JTAG [P3] [UNVERIFIED]
- **Evidence:** `automoto.repl:27-28` ("USB Serial JTAG / Debug Console", `UART.PL011`); `sim/README.md:16` ("USB JTAG/UART0 Konsolu"); `PCB_SPECIFICATION.md:160` IO19 = USB_DM.
- **Fix sketch:** Name it correctly after checking the TRM; model with `ESP32_USBSerialJTAG` if that is what the console uses.

### F-06-23 - Modem power-cycle can toggle a working modem off [P2] [INFERRED]
- **Evidence:** `main.c:51-56` calls `modem_power_cycle()` every 3 s whenever `modem_is_alive()` is false; `modem.c:48-56` pulses PWRKEY 1.2 s (SIM808 PWRKEY is a toggle [UNVERIFIED]); STATUS read is pull-up biased (F-06-06).
- **Consequence:** A modem that is on but reads LOW gets PWRKEY pulses every ~3.2 s, forever.
- **Fix sketch:** Back off exponentially; cap attempts; only pulse after a confirmed-off state.

---

## 9. Open Questions

1. **Renode GPIO / TWDT model names for ESP32-S3** — which types exist in this Renode build? (`strings Infrastructure.dll` shows `ESP32_TIMG`, `ESP32_RTC_CNTL`, but no GPIO type found.) Needs `peripherals` on a loaded S3 machine plus source/doc of the installed build.
2. **Is the S3 boot ROM / reset vector modeled?** The `0x50000000` abort suggests no. Needs an IDF-built boot image or Renode's `esp32s3` reset-vector setting.
3. **Is the production BOM part really octal PSRAM?** The name `N16R8` suggests yes; the firmware never enables it. Confirm with the Espressif datasheet and the chosen ordering code.
4. **Does the PCB implement the neutral interlock in hardware (series with the SSR starter path)?** The repo shows only a sense input (PCB_SPECIFICATION.md:167, 116, 122). Needs schematic review (`hardware/pcb/automoto.kicad_sch`), not in this scope.
5. **What is the SIM808 vs SIM7080G vs EG915U decision?** Three modems are referenced (PROJECT.md:39, 60-61, 69-73). The firmware path (`modem_init(MODEM_TYPE_SIM808)`, main.c:125) is hard-coded to SIM808 while the EG915U path is only a log string (modem.c:20).
6. **Was Renode's `-P -1` (sim/README.md:41) a valid port argument?** [UNVERIFIED]; not tested.
7. **Who is the intended owner of the mock/production split?** Needed to pick between Kconfig and PlatformIO env for §5a.

---

## Suggested Jobs

Priority order. Each job lists what it would fix.

1. **[P0] Route all actuator commands through one choke point (F-06-01).** Refactor `ble_keyless` to call `actuator_request_ignition`; make `board_set_ignition(true)` refuse while `failsafe_get_kill_state() != IDLE`. *Blocks:* BLE → lockout bypass.
2. **[P0] Build-gate the mocks (F-06-02, F-06-03).** Add `AUTOMOTO_SIM_MOCKS` macro/Kconfig, `#error` guard for release builds, `[env:sim]` in `platformio.ini`, and an ELF string-scan gate for `38.4237`. *Blocks:* silent fake GNSS/accel shipping.
3. **[P1] Extract pure interlock/soft-kill/crank functions (F-06-15, §5c Option B).** Create `firmware/lib/automoto_logic/` (or `components/`) with no FreeRTOS in the decision path. *Enables:* every host unit test below.
4. **[P1] Host unit test suite (pure functions + fake board/clock).** Cases: crank rejected in ignition-off (actuator_safety.c:50), in gear (:55), mid-crank neutral loss (:100), 1500 ms hard limit under queue bursts (F-06-08), soft-kill stage 3 never at speed (F-06-13), BLE RTT boundaries (F-06-12), lockout vs BLE (F-06-01), `gps_fixed=false` handling (F-06-02).
5. **[P1] Fix the timer (F-06-08).** Wall-clock deadline via `esp_timer_get_time()`.
6. **[P1] Modem driver correctness (F-06-06, F-06-07, F-06-23).** Explicit `OK`/`ERROR` parsing; STATUS pull-down; power-cycle backoff. Mock default → `ERROR` for unknowns.
7. **[P1] Real LIS3DH driver and motion→siren wiring (F-06-03).** WHO_AM_I, INT latched, GPIO4 configured.
8. **[P1] OTA self-test gate (F-06-09).** HIL-tested rollback.
9. **[P1] Production sdkconfig overlay: Secure Boot v2 + flash encryption (F-06-10).** Dev overlay stays unsigned.
10. **[P1] Renode repl fidelity (F-06-04, F-06-05).** Switch to `UART.ESP32_UART`; add GPIO/TIMG models once identified; fix CWD dependence; the 10-line smoke test in §1 is the acceptance test.
11. **[P1] BLE token verification (F-06-12).** AES-128-GCM with mbedtls; capture timestamp in the BLE callback.
12. **[P1] MQTT contract implementation with a doc-as-test check (F-06-14).**
13. **[P1] CI (F-06-16).** GitHub Actions: `pio test -e native`, `pio run -e esp32s3_automoto` (build-only). Add `renode-test` later for the smoke test.
14. **[P2] Deep-sleep path and wake-source fix (F-06-11); TWDT coverage (F-06-19); PSRAM decision (F-06-18); Wokwi `wokwi.toml` (F-06-17); neutral sense short check (F-06-20).**
15. **[P3] Doc drift cleanup (D-08..D-20), `.gitignore` (F-06-21), uart0 naming (F-06-22).**

### Test pyramid (Q9)

**Headline:** Make the interlocks provable on the host first, because that is the only layer that can run on every commit with no hardware. Simulation is for integration only and is currently not fit for safety evidence. HIL is the release gate. Fault injection is the last line before field trials.

| Layer | What it covers | Specific defects it would have caught in this repo |
|---|---|---|
| **L0 Host unit tests** (`pio test -e native` or CMake host; fake board/clock; no FreeRTOS in decision path) | Crank interlock (actuator_safety.c:48-68, 98-114), soft-kill state machine (failsafe.c:12-47), BLE RTT + token (ble_keyless.c:31-54), modem response parsing (modem.c:63-80), GNSS gating (modem.c:82-91) | **F-06-01** BLE bypass of lockout (ble_keyless.c:52). **F-06-02** `speed=0` permanent gate. **F-06-08** loop-count hard limit under queue bursts. **F-06-12** unverified token and caller-supplied RTT. **F-06-13** stage 3 at speed. **F-06-07** `ERROR` treated as success. |
| **L1 Simulation integration** (Renode with fixed repl; Wokwi for GPIO demo; mock modem with `ERROR` default) | Boot path, task wiring, GPIO state at init, UART1 AT round-trip, ELF/launch reproducibility | **F-06-04** PL011 vs ESP32_UART and no GPIO model. **F-06-05** CWD and ELF path. **F-06-06** GSM LED lit with no modem (Wokwi). **D-10/D-09** mock overclaim. Mock default-OK masking missing commands (mock:100-102). |
| **L2 HIL rig** (dev board + real SIM808 + LIS3DH + optocoupler + PROFET/SSR load; µA meter; scope on GPIO) | Real AT registration, STATUS line behaviour, neutral switch short, deep-sleep current, OTA rollback with injected fault, PSRAM presence, SB/FE eFuse state | **F-06-06** STATUS pull-up. **F-06-09** OTA confirm with dead modem. **F-06-11** never sleeps. **F-06-10** unsigned image accepted on dev board (signature verify step). **F-06-20** neutral short bypass. **F-06-18** PSRAM not detected. |
| **L3 Fault injection** (HIL + scripted: cut neutral wire mid-crank; starve actuator task >3 s; drop modem mid-session; power loss in soft-kill stage 3; replay BLE response at >18 ms; feed GNSS mock into release build) | Watchdog and reset behaviour, relay state after panic, lockout persistence across reset, replay/relay resistance, mock-leakage detection | **F-06-19** TWDT scope and reset relay state. **F-06-20** cut-wire/short. **F-06-01** lockout lost on reset (NVS/RAM state). **F-06-12** relay attack at delayed RTT. **F-06-02/03** mock values in release. |

**Minimum viable pyramid to start (in order):**
1. Extract the three pure functions (§5c Option B).
2. Write the L0 tests for F-06-01, 02, 08, 12, 13 (these are the P0/P1 safety rules).
3. Add `pio test -e native` + build-only CI.
4. Only then invest in L1 (fix the repl first).
5. L2/L3 when the first HW rig exists.

---

*Report generated by read-only analysis. No firmware was compiled or run. Renode checks were run only in `/tmp/opencode/t6/`. Items marked [UNVERIFIED] require the stated proof before being relied on.*
