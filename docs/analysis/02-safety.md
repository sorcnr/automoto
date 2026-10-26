# 02 - Fail-Safe Invariants & Rider/Theft Safety

## Summary

- **No actuation path is reachable from any external input in the current tree.** `actuator_request_ignition`, `actuator_request_crank`, `actuator_request_emergency_shutdown`, `failsafe_trigger_soft_kill`, `failsafe_cancel_soft_kill`, `ble_keyless_verify_challenge_response`, and `power_manager_enter_deep_sleep` have zero call sites outside their own definitions (grep over `firmware/`, verified). There is no MQTT handler (`firmware/main/` contains no MQTT file; `main.c:43` mentions MQTT only in a comment). The findings below are therefore **latent**: they become live the moment REMOTE_START / REMOTE_KILL / Keyless wiring lands. Severity is assigned on that basis; I have not rated any latent defect P0 on its consequence alone (see Scope & Method, "Severity rule").
- **The claimed invariants are mostly unenforced in code.** Default-safe outputs are enforced after `board_pins_init` only (`board_pins.c:37-45`). "Never crank in gear" rests on a single unfiltered, fail-unsafe sense line with no electrical series interlock, contrary to `SECURITY_SPECIFICATION.md:139-140`. "Never hard-cut at speed" is **falsified**: the soft-kill stage-3 hard cut fires at t≈5 s with no speed input (`failsafe.c:33-36`). The "TWDT forces outputs safe" claim (`firmware/README.md:38`) has **no implementation** (no callback, no panic hook, no `gpio_hold`).
- **Soft-kill is speed-blind (F-02-02).** A bike at 60 km/h receives 3 s of 15 ms kill pulses (~50 m at 60 km/h), 2 s of siren at any speed, then a full ignition cut and kill-SSR assertion at t≈5 s. This contradicts `SECURITY_SPECIFICATION.md:134-138` (gate on <20 km/h and V=0). Rated P1 today (no caller), **P0 at the moment any remote-kill caller is added**.
- **There is no trustworthy speed source (F-02-03).** GNSS speed is hard-coded `0.0` (`modem.c:88`); the IMU returns constants (`sensors_imu.c:37-39`); the LIS3DH is never configured (`sensors_imu.c:44-47`). Any "V=0" gate written against this code would pass immediately and fire the lockout at full speed.
- **Neutral interlock is fail-unsafe (F-02-01).** An open, cut, or unplugged neutral-sense line reads as NEUTRAL (`board_pins.c:96`) and admits cranking. There is no debounce, no electrical series path from neutral to the starter SSR (netlist: `generate_kicad_pcb.py:1249`, `1252-1254`), and the 20 ms sampling is single-shot at command time. Rated P1; P0 on wiring of any crank path.

## Scope & Method

**Files read (full):** `firmware/main/actuator_safety.{c,h}`, `failsafe.{c,h}`, `board_pins.{c,h}`, `power_manager.{c,h}`, `main.c`, `ble_keyless.{c,h}`, `sensors_imu.{c,h}`, `modem.{c,h}`, `firmware/main/CMakeLists.txt`, `firmware/sdkconfig.defaults`, `firmware/README.md`, `firmware/SECURITY_SPECIFICATION.md` (§1-6), `PROJECT.md` (§2-7), `docs/TARGET_MARKET_AND_USE_CASES.md` (§4-5), `hardware/pcb/PCB_SPECIFICATION.md` (pin/BOM tables), `hardware/pcb/generate_kicad_pcb.py` (netlist, lines 1201-1290), `hardware/pcb/generate_kicad_sch.py` (lines 700-715), `sim/wokwi/diagram.json` (neutral button only), `sim/tools/mock_sim808.py` (speed field), `sim/README.md` §2.1. `firmware/platformio.ini`, `firmware/partitions.csv`, `firmware/CMakeLists.txt` were not opened in depth (not needed for the findings).

**Method:** static reading and call-graph grep only. No build, no run.

**Could not verify (explicit):**
- ESP-IDF/FreeRTOS semantics: `configMAX_PRIORITIES` default, `vTaskDelete` on a task running on the other core, `xQueueReceive` timeout rounding at 1 kHz tick, ESP32-S3 GPIO reset/deep-sleep pad state, strapping pins, RTC GPIO list. All tagged UNVERIFIED where used.
- LTV-356T pinout: taken from the Liteon datasheet excerpt (Anode 1, Cathode 2, Emitter 3, Collector 4) via web search; UNVERIFIED against the physical part.
- Bike neutral-switch convention (closed-in-neutral vs closed-in-gear) for the target motorcycles: UNVERIFIED. The conclusion for an open/cut line does not depend on it.
- BLE controller/host task priorities on Core 0 (preemption of the actuator task): not in repo; UNVERIFIED.
- Mechanical contact-bounce duration and internal pull-up value of ESP32-S3 pads: typical values only, UNVERIFIED.

**Severity rule applied:** Spec definitions (P0 = safety-of-life or theft-enabling). A defect whose entry point has **no caller in the current tree** is rated P1 ("blocks production release") and flagged "P0 on wiring". This follows the instruction not to inflate stubs to P0. The one exception is hardware/firmware contract defects that ship on the PCB regardless of firmware callers; they are still rated P1 because the firmware cannot reach them until wiring.

**Cross-check sources:** `SECURITY_SPECIFICATION.md` §5 (lines 130-142), `PROJECT.md` §2.1-2.3 (lines 13-24), §4 (79-82), §6 (157-160), `TARGET_MARKET` §4-5.

---

## Findings

### Invariant-by-invariant proof table

| # | Invariant (as claimed) | Claimed where | Enforced at (path:line) | Verdict |
|---|---|---|---|---|
| I1 | Default-safe outputs: all relays/SSR/siren LOW (NO) after reset/power-on | `SECURITY_SPECIFICATION.md:141-142`; `PROJECT.md:160`; `board_pins.c:11`, `:36-37` | `board_pins.c:23-34` (gpio_config OUTPUT, pulldown), `:37-45` (drive LOW); called first-in-chain at `main.c:105` before any actuator task (`main.c:111`) | **PARTIAL.** Enforced after `board_pins_init`. Before it (bootloader, ROM, reset window, `app_main` steps 1 at `main.c:97-102` which is NVS only) the pad state is reset-default and not verified (UNVERIFIED for GPIO3 strapping, GPIO46 strapping, GPIO8/9). Note: `board_pins_init` uses `gpio_config` then `gpio_set_level`, which is correct ordering. |
| I2 | Never crank in gear | `SECURITY_SPECIFICATION.md:139-140` ("mantıksal ve elektriksel"); `PROJECT.md:158`; `actuator_safety.c:54-58` | Software only: `actuator_safety.c:55` (command time), `actuator_safety.c:100` (in-loop), `board_pins.c:75` (board-level). **No electrical series path**: `U11` (starter SSR) is fed from `+12V_IN` and driven from `STARTER_CTRL` only (`generate_kicad_pcb.py:1249`); `NEUTRAL_OUT` goes only to `U1` pin 20 and `R14` (`:1201`, `:1253-1254`). | **FALSIFIED** for open/cut/unplugged neutral line (F-02-01). Also violates the "electrical" half of `SECURITY_SPECIFICATION.md:140` in the netlist. |
| I3 | Never hard-cut ignition at speed (soft-kill; remote kill deferred until V=0) | `SECURITY_SPECIFICATION.md:134-135`; `TARGET_MARKET` §5 (lines 113-154); `PROJECT.md:158-159` (queue until stopped) | No speed input anywhere. Stage 3 fires on a timer: `failsafe.c:33-36` (ignition OFF + kill ON at t≈5 s). `ACT_CMD_EMERGENCY_SHUTDOWN` executes immediately: `actuator_safety.c:85-93`. `ACT_CMD_IGNITION_SET(false)`: `actuator_safety.c:38-39` - no speed check. | **FALSIFIED** (F-02-02, F-02-04). |
| I4 | Crank ≤ 1500 ms | `actuator_safety.h:12`; `firmware/README.md:39`; `sim/README.md` §2.1 ("en geç 1500 ms") | Clamp `actuator_safety.c:61-63`; countdown `actuator_safety.c:98-113` (decrement `-= 20` per loop, `:112`); no monotonic clock. | **PARTIAL / FALSIFIED as an absolute bound.** Nominal ~1.48 s, but: (a) repeated `CRANK_START` re-arms with no cumulative cap (`actuator_safety.c:64-66`, no `s_cranking_active` guard); (b) a stalled loop cannot cut the starter (F-02-06, F-02-07). |
| I5 | TWDT forces all outputs safe on hang | `firmware/README.md:38`; `actuator_safety.c:22-26` (registration only) | **No code.** No `esp_task_wdt` callback, no panic hook, no `gpio_hold_en`. Only `CONFIG_ESP_TASK_WDT_PANIC=y` (`sdkconfig.defaults:23`, timeout `:20`=3 s) makes it panic; reset-default pad state is the only mechanism. | **FALSIFIED** as documented (F-02-06). Reset-default state = UNVERIFIED. |
| I6 | Soft-kill stage 2 siren only when <20 km/h; stage 3 only at V=0 | `SECURITY_SPECIFICATION.md:137-138`; `failsafe.h:13-15` comments | Timer only: `failsafe.c:19-24` (100×30 ms), `:27-30` (2 s siren), `:33-36`. No speed/V read anywhere. | **FALSIFIED** (F-02-02). |
| I7 | Ignition only via verified keyless (RTT + token) | `PROJECT.md:19-20`; `SECURITY_SPECIFICATION.md:52-62` (signed token + RTT) | `ble_keyless.c:42-47` (RTT only), `:49-50` (comment "Token Teyidi" - **no code**), `:52` (`board_set_ignition(true)` - bypasses actuator queue and `s_ignition_active`). Caller: none. | **FALSIFIED** in code (no token check); latent (F-02-08). |
| I8 | Deep sleep leaves outputs in default-safe state | `PROJECT.md:79-82`; `SECURITY_SPECIFICATION.md:141-142` | `power_manager.c:45-48` forces KILL, STARTER, SIREN low but **not** `PROFET_IN` (GPIO8) / `PROFET_DEN` (GPIO15); no `gpio_hold_en` anywhere (grep, verified). `esp_deep_sleep_start()` at `power_manager.c:51` - caller: none. | **FALSIFIED** in code; latent (F-02-09). |
| I9 | Emergency shutdown is recoverable by the owner | (no spec requirement; implied by `PROJECT.md:19-20` "kontak kapanır/açılır") | Latch: `actuator_safety.c:87-92` sets kill=1; release only via `ACT_CMD_KILL_SSR_SET` (`:81-83`, no sender) or `failsafe_cancel_soft_kill` (`failsafe.c:76-77`, no caller). API `actuator_safety.h:36-39` exposes no release. | **Not claimed, but absent**: recovery = reboot only (F-02-10). |
| I10 | Single authoritative owner of PROFET/SSR/siren (TWDT-supervised) | `firmware/README.md:35-38` ("izole", "Donanımsal Bekçi"); `actuator_safety.c:22-26` (TWDT registration) | Four writers: `actuator_safety.c` (task, `:40-109`), `failsafe.c` (`:20-36`, `:76-77`), `ble_keyless.c:52`, `power_manager.c:46-48`. | **FALSIFIED** (F-02-05). |

---

### F-02-01 - Neutral sense is fail-unsafe: open/cut/unplugged line reads NEUTRAL; no debounce, no electrical interlock [P1 - P0 on wiring] [VERIFIED netlist+code; polarity INFERRED]

**Evidence**
- Firmware: `board_is_neutral()` returns `gpio_get_level(PIN_SENSE_NEUTRAL) == 0` (`board_pins.c:93-97`), comment "Active LOW" (`:95`). Pin = GPIO12 (`board_pins.h:30`). Pull-up enabled on GPIO12 (`board_pins.c:51`).
- Netlist (`hardware/pcb/generate_kicad_pcb.py`): `R13` (4.7 kΩ) from `+12V_IN` to `NEUTRAL_ANODE` (`:1252`); `U9` pin1 anode = `NEUTRAL_ANODE`, pin2 cathode = `NEUTRAL_SENSE`, pin4 collector = `+3V3`, pin3 emitter = `NEUTRAL_OUT` (`:1253`); `R14` 10 kΩ `NEUTRAL_OUT`→GND (`:1254`); `NEUTRAL_OUT` → `U1` pin 20 = IO12 (`:1201`); `NEUTRAL_SENSE` → `J1` pin 8 = external neutral switch (`:1273`).
- LTV-356T pin order (Liteon datasheet, UNVERIFIED on the physical part): 1 Anode, 2 Cathode, 3 Emitter, 4 Collector.
- Therefore: LED (and thus transistor) conducts only when the external switch closes `NEUTRAL_SENSE` to GND. When it does, `NEUTRAL_OUT` ≈ 3.1 V → GPIO HIGH. When the line is open, the LED is off and `R14` pulls `NEUTRAL_OUT` LOW → GPIO LOW → firmware reads **NEUTRAL**.
- Drive margin (INFERRED): at 12.6 V through 4.7 kΩ and a grounded switch, I_F ≈ (12.6−1.2)/4.7k ≈ 2.4 mA, below the 5 mA CTR test condition in the datasheet excerpt (UNVERIFIED value; datasheet summary says CTR ≥50% at 5 mA).
- No debounce or filter: single `gpio_get_level` per sample, sampled at command time (`actuator_safety.c:55`), again in `board_set_starter` (`board_pins.c:75`), and every loop iteration while cranking (`actuator_safety.c:100`). Sampling period 20 ms (`actuator_safety.c:28`).
- No electrical series interlock: the starter SSR `U11` is driven only from `STARTER_CTRL` and fed from `+12V_IN` (`generate_kicad_pcb.py:1249`); neutral does not enter the `U11` power path. `SECURITY_SPECIFICATION.md:140` claims the starter SSR is "mantıksal ve elektriksel olarak" tied to the neutral switch. The netlist does not implement that.
- Doc/BOM drift: `PCB_SPECIFICATION.md:116` says R4 (10 kΩ) is the SENSE_NEUTRAL pull-up; netlist R4 is `+3V3`→`ESP_EN` (`generate_kicad_pcb.py:1207`). `PCB_SPECIFICATION.md:123` says R14 is 100 kΩ (Q1 gate bias); netlist R14 is 10 kΩ NEUTRAL pulldown (`:1254`, `generate_kicad_sch.py:711`).

**Failure mode + trigger**
- Trigger A (static): neutral-sense wire cut, connector J1 unplugged, switch open-circuit failure. Result: LED off → GPIO LOW → "NEUTRAL" → crank permitted (`actuator_safety.c:55` passes) provided ignition is on and a CRANK_START arrives.
- Trigger B (convention): if the bike's switch closes to ground in NEUTRAL (the usual convention, UNVERIFIED for target bikes), then the in-gear state reads LOW = NEUTRAL too. Under that convention the sensor is inverted in normal operation, and the firmware would refuse crank in neutral but permit it in gear.
- Trigger C (transient, see F-02-11): contact bounce or a wet-connector glitch sampled LOW while in gear at command time.

**Consequence**
- Starter engaged with the bike in gear. Cranking the engine through the gearbox drives the rear wheel: a bike with a rider or an unattended bike moves. Safety-of-life (rider on bike) and theft-enabling (ride-away) per `SECURITY_SPECIFICATION.md:10`.
- Reachability today: none (no caller of `actuator_request_crank`; no ignition source, see I7). Hence P1 now, P0 when REMOTE_START or the BLE path is wired.

**Fix sketch**
1. Invert the logic so that **only a positive, electrically confirmed NEUTRAL** permits crank. Use a separate "sense OK" check: `neutral_ok = (level_neutral_asserted) && (sense_line_not_open)`; an open line must be treated as IN GEAR.
2. Add a hardware series path: route the neutral contact in series with the `U11` starter SSR drive (or the SSR's +12 V feed), so the MCU cannot energise the starter without the physical contact closed.
3. Remove the internal GPIO pull-up (`board_pins.c:51`) that fights the external network, or document the intended pull.
4. Add a known-good self-test at ignition-on: the sensor must read IN GEAR with a clutch-out simulation, and a stuck or open line must latch a fault.
5. Reconcile BOM/spec drift (R4, R14) before any board run.

**Verification**
- Static: confirm the switch polarity on the target bikes (UNVERIFIED; need the wiring diagram of the bikes the product is sold for).
- Bench (not run here): open J1.8 with a known-good ignition and verify the crank command is refused after the fix.
- Host unit test (proposed): fake `gpio_get_level` returning LOW for open line; assert crank rejected after fix.

---

### F-02-02 - Soft-kill is speed-blind: stage 3 hard-cuts ignition and kill SSR at t≈5 s at any speed [P1 today - P0 on wiring] [VERIFIED code; physical consequence INFERRED]

**Evidence**
- Stage 1: `failsafe.c:19-24`, 100 cycles × (15 ms on + 15 ms off) = 3.0 s of kill-SSR pulsing; no speed read.
- Stage 2: `failsafe.c:29-30`: siren ON, `vTaskDelay(2000)`. Comment (`failsafe.c:28`) "Hız..." is absent; the spec requires <20 km/h (`SECURITY_SPECIFICATION.md:137`). The code does not check.
- Stage 3: `failsafe.c:33-36`: `board_set_ignition(false)` (PROFET OFF) and `board_set_kill_ssr(true)` (kill asserted) at t≈5.0 s, unconditionally. The spec requires V=0 confirmation (`SECURITY_SPECIFICATION.md:138`; `failsafe.h:15` comment).
- Trigger: `failsafe_trigger_soft_kill()` at `failsafe.c:55-68`. Callers: none (grep, verified).

**Failure mode + trigger**
- Trigger: any future remote-kill / theft-alarm path calls `failsafe_trigger_soft_kill()` while the bike is moving (the scenario `TARGET_MARKET` §5 describes, lines 113-154). For a bike at 60 km/h:
  - t = 0-3 s: ignition still ON; kill SSR pulses 50% duty every 30 ms. The pulse train may reduce torque (INFERRED: 15 ms blocks vs 4-stroke firing interval; magnitude UNVERIFIED).
  - Distance covered in 3 s at 16.7 m/s: ~50 m (before any deceleration).
  - t = 3-5 s: siren ON, rider and bystanders alerted, ignition still ON, speed still approximately 60 km/h (no speed-dependent check).
  - t = 5 s: PROFET OFF and kill asserted. The engine loses drive instantly. Distance to this point ~83 m with no deceleration assumed.
- Spec compliance: the code violates `SECURITY_SPECIFICATION.md:134-138` (no gating at <20 km/h, no V=0) and `TARGET_MARKET` §5 (`Hız 70 -> 40 -> 20 km/h` band, lines 127-128).

**Consequence**
- A bike at 60 km/h is hard-cut at t≈5 s. Engine braking and drive vanish at speed; the rear wheel may lose traction if the rider downshifts or brakes at the moment of cut (INFERRED from the spec's own premise, `SECURITY_SPECIFICATION.md:135`; not measured). Rider injury is the safety-of-life consequence. The theft purpose (stop the bike) is only met if the thief has already slowed.
- Theft side: a thief who keeps throttle at 60 km/h gets 5 s, then the bike dies at speed, which is the outcome the spec was written to prevent (`SECURITY_SPECIFICATION.md:135`).

**Priority justification**
- Refuted as a current-tree P0 (no caller; see Summary). Confirmed as the top safety defect in the design: every remote-kill feature in the spec routes through this function.

**Fix sketch**
1. Gate stage 2 on measured speed < 20 km/h and stage 3 on speed == 0 **held for N seconds** from an independent source (see F-02-03). Until both are available, do **not** call `failsafe_trigger_soft_kill()` from any path.
2. Make stage 3 conditional: if speed never reaches 0 within a timeout, keep stage 1 (pulsing) and alarm rather than hard-cut.
3. Route all writes through the actuator task (see F-02-05).

**Verification**
- Static only here. Proposed: host test driving a fake speed source (60 → 0 km/h ramp) and asserting no PROFET OFF before the V=0 condition.
- Physical test on a bench rig (not performed): measure time-to-zero-speed under pulsed ignition; UNVERIFIED.

---

### F-02-03 - No speed source exists; any V=0 gate would pass at 60 km/h [P1] [VERIFIED]

**Evidence**
- GNSS: `modem_get_gnss_fix()` returns hard-coded `latitude=38.4237, longitude=27.1428, speed_kmh=0.0f, gps_fixed=true` (`modem.c:82-91`, specifically `:86-90`). No AT command (`AT+CGNSINF` is not sent anywhere in `firmware/`; grep, verified).
- Telemetry prints the fake fix every 3 s (`main.c:59-64`).
- IMU: `sensors_imu_read_accel()` returns `x=0, y=0, z=1000` (`sensors_imu.c:37-39`, comment "1G yerçekimi varsayımı" = assumed 1 g). `motion_detected` is a raw read of `PIN_IMU_INT1` (`sensors_imu.c:40`), which `board_pins_init` does not configure (`board_pins.c:12-59` lists only output pins and neutral/modem inputs).
- The LIS3DH is never configured: `sensors_imu_init()` only installs the I2C driver (`sensors_imu.c:24-31`); `sensors_imu_configure_wakeup_threshold()` only logs (`:44-47`).
- Simulation: `sim/tools/mock_sim808.py:31` default `speed_kmh = 0.0`; `:44` prints it in CGNSINF. A V=0 gate would be satisfied in the simulator at all times.
- CAN speed (ISO 19689 path, `SN65HVD230`): no TWAI/CAN code in `firmware/` (grep, verified).

**Failure mode + trigger**
- Any gate of the form `if (speed == 0) lockout();` evaluated against `modem_get_gnss_fix` fires immediately at any speed, because the speed is constant 0.
- A "stationarity" check from the IMU is possible only as a vibration heuristic: an idling bike at a light is vibrating; a bike on its stand is not. Double integration of acceleration drifts within seconds (INFERRED).
- GNSS speed from SIM808 1 Hz CGNSINF has latency and is spoofable/jammable (UNVERIFIED for the module used).

**Consequence**
- A future V=0 gate would hard-cut at speed (the F-02-02 outcome), and it would be **invisible in simulation**, so a passing sim run gives false assurance.

**Fix sketch**
1. Implement real CGNSINF parsing (`modem.c`); treat `gps_fixed == false` or stale fix (>3 s) as "speed unknown → do not lock out".
2. Add CAN speed (ISO 19689) if available; cross-check GNSS vs CAN.
3. Make the simulator default to a **non-zero** moving speed profile so a V=0 gate cannot pass by default.
4. Treat "speed unknown" as "moving" for lockout decisions.

**Verification**
- Static: reading. Proposed: sim test with speed ramp; assert lockout blocked while speed unknown.

---

### F-02-04 - Remote shutdown and ignition-off execute immediately, violating PROJECT §6 deferral; emergency command can be dropped [P1] [VERIFIED]

**Evidence**
- `ACT_CMD_EMERGENCY_SHUTDOWN` handled at `actuator_safety.c:85-93` with no speed check; `ACT_CMD_IGNITION_SET(false)` at `:38-39` ditto.
- `PROJECT.md:158-159` (§6, "Sürüş Esnasında Emniyet Kapatma Koruması"): "Araç hareket halindeyken uzaktan emniyet kapatma devreye alınmaz; aracın hızı sıfıra inip durana kadar komut kuyrukta bekletilir." Not implemented; the opposite happens.
- `SECURITY_SPECIFICATION.md:134` and `TARGET_MARKET` §5 require the opposite of §6 for a theft kill: soft-kill **while moving**. Spec conflict (see Open Questions).
- Queue drop: `actuator_send_cmd` uses `xQueueSend(..., pdMS_TO_TICKS(50))` and returns `ESP_ERR_TIMEOUT` on full (`actuator_safety.c:152-155`). Queue depth 10 (`actuator_safety.h:13`). EMERGENCY is an ordinary queued message (no priority, no latch).
- Callers of `actuator_request_emergency_shutdown`: none.

**Failure mode + trigger**
- Trigger 1: remote kill while moving → hard cut (see F-02-02 design; here it is immediate, not 5 s).
- Trigger 2: queue saturated by repeated commands (e.g., CRANK_START spam) → EMERGENCY returns TIMEOUT and is lost; a caller that ignores the return value leaves the bike running (INFERRED, depends on caller).

**Consequence**
- Immediate hard cut at speed (rider risk), or a silently lost emergency kill (theft risk).

**Fix sketch**
1. Emergency kill as a **latched flag** read by the task on every loop, not a queued message.
2. Defer the lockout until speed == 0 for ≥N s (PROJECT §6), and separately implement soft-kill for the theft case (decide which: see Open Questions).
3. Check the return of every `actuator_send_cmd`; retry or escalate to a latch on failure.

**Verification**
- Static. Proposed: host test: fill queue, send EMERGENCY, assert kill latch set.

---

### F-02-05 - Actuator ownership violated: four writers to PROFET/SSR/siren; cancel overrides emergency kill; stage 3 does not update actuator state [P1] [VERIFIED code; race consequences INFERRED]

**Evidence**
- TWDT-supervised owner: `actuator_safety.c:131-139`, priority `configMAX_PRIORITIES - 2` (= -2), core 0.
- Second writer: `failsafe.c:58-66` creates `soft_kill_worker_task` at `configMAX_PRIORITIES - 1` (higher than the owner), core 0. Not registered with TWDT (no `esp_task_wdt_add` in `failsafe.c`; grep verified).
- Writes from the soft-kill task: kill toggling `failsafe.c:20-22`; siren `:29`, `:40-42`; ignition off `:35`; kill ON `:36`.
- Writes from cancel (any context): `failsafe.c:76-77` (siren OFF, kill OFF), `:72-75` (vTaskDelete).
- Third writer: `ble_keyless.c:52` `board_set_ignition(true)` directly, from the NimBLE callback context (not in repo; caller none).
- Fourth writer: `power_manager.c:46-48` (sleep path).
- Ownership state: the actuator's `s_ignition_active` (`actuator_safety.c:14`) is never updated by failsafe (`failsafe.c` has no reference to it) or by `ble_keyless.c:52`.

**Concrete race (sequence, assuming the wiring exists)**
1. Actuator processes `ACT_CMD_EMERGENCY_SHUTDOWN`: `s_ignition_active=false`, PROFET OFF, kill ON (`actuator_safety.c:87-92`).
2. Soft-kill (priority -1, pre-empts the owner on every wake) runs stage 1: `board_set_kill_ssr(false)` at `failsafe.c:22` - kill released within ≤15 ms of step 1 if the soft-kill was already active. Stage 3 then sets kill ON again at `failsafe.c:36`.
3. Consequence with PROFET OFF: little, because ignition power is already cut (PROFET is the real switch). **But**: if a `BLE`/`IGNITION_SET(true)` then re-enables PROFET while kill is released (step 2 window), the engine can run with the emergency still "latched" in the actuator's view.
4. Cancel (`failsafe.c:76-77`) releases kill and siren from another context after an EMERGENCY kill was latched: `kill=0` overrides the actuator's latched state with no message to the owner. Ignition re-enable (`actuator_safety.c:39-40`) now produces an engine that runs.
5. Stage 3 sets PROFET OFF (`failsafe.c:35`) but never sets `s_ignition_active=false`. Actuator still reports ignition ON; `ACT_CMD_CRANK_START` passes its ignition check (`actuator_safety.c:50`), so `board_set_starter(true)` engages the starter after the lockout (`actuator_safety.c:66`). The starter SSR is not on the PROFET path (netlist `U11` fed from `+12V_IN`, `generate_kicad_pcb.py:1249`), so the starter can crank without spark. The "lockout" (`SECURITY_SPECIFICATION.md:138`, "marşı kilitler") is not achieved for the starter.
6. `ble_keyless.c:52` can set PROFET ON after stage 3 (no check of `current_kill_state`). Kill still asserted (only cancel or reboot releases it), so the engine remains dead, but the PROFET state is now controlled by an unsynchronised path.

**Priority detail**
- Soft-kill at -1 pre-empts the owner at -2 for each `vTaskDelay` wake. Per-preemption cost is one GPIO write (µs); 100 wake-ups in stage 1 add µs-scale jitter. Not a timing failure for the owner's 20 ms loop (INFERRED; ESP-IDF priority semantics UNVERIFIED for the Core-0 BT tasks).
- Owner starvation by a higher-priority task on Core 0 would trigger TWDT after 3 s (`sdkconfig.defaults:20`, `:23`), but the soft-kill task is not monitored, so a soft-kill stall is invisible.

**Failure mode + trigger**
- Trigger: any remote/BLE/alarm event that calls both `failsafe_*` and `actuator_*` within the same lockout window.

**Consequence**
- Engine re-enabled while the actuator believes the emergency is latched; starter engaged after "lockout"; telemetry (`main.c:63-64`) reports values that do not match the physical PROFET/kill state.

**Fix sketch**
1. Single owner: failsafe requests transitions via `actuator_send_cmd` (or an internal state machine inside the owner task). No direct `board_set_*` calls outside the owner.
2. Failsafe state and kill latch live in the owner; cancel is a message, not a `vTaskDelete`.
3. Register the soft-kill task (or fold it into the owner) under TWDT.

**Verification**
- Static. Proposed: model-check or unit test the state machine with interleavings of {EMERGENCY, CANCEL, STAGE3, IGNITION(true), CRANK}.

---

### F-02-06 - "TWDT forces outputs safe" is not implemented; a stalled actuator leaves starter/kill as last written until reset [P1] [VERIFIED absence; reset-default state UNVERIFIED]

**Evidence**
- Claim: `firmware/README.md:38` ("anında panic üreterek tüm röleleri 0 ... seviyesine çeker"); repeated in `sim/README.md` §2.1 (TWDT bullet).
- Code: TWDT registration (`actuator_safety.c:22-26`); feed (`:33`). No `esp_task_wdt` callback, no `esp_register_shutdown_handler`, no `gpio_hold_en`, no `gpio_set_level` in any fault path (grep over `firmware/main`: `gpio_set_level` appears only in `board_pins.c`, `power_manager.c`, `modem.c`, `main.c` LED toggles, `ble_keyless.c:23`).
- sdkconfig: `CONFIG_ESP_TASK_WDT_PANIC=y` (`sdkconfig.defaults:23`), timeout 3 s (`:20`), idle tasks watched (`:21-22`).
- The watchdog monitors only the actuator task; `soft_kill_worker_task` (`failsafe.c:58-66`) and `cellular_core1_task` (`main.c:131-132`) are not registered (`main.c:131-132` have no `esp_task_wdt_add`).

**Failure mode + trigger**
- Trigger: the actuator task blocks for ≥3 s while `s_cranking_active` (e.g., starved by a higher-priority task on Core 0, or a deadlock in a logging call). The 1500 ms cut (`actuator_safety.c:98-113`) runs inside the same task and cannot fire.
- Outcome: starter SSR stays at its last written level until TWDT panics (≤3 s after last feed, plus panic/reboot time), then depends on reset-default pad state (UNVERIFIED).

**Consequence**
- Starter energised for ~3 s instead of 1.5 s (cranking in neutral: battery/starter damage, P2 consequence). In gear: same F-02-01 hazard, longer. Kill SSR last-state is retained during the stall; if it was ON (emergency), it stays ON (fail-safe for the rider); if it was OFF, the engine is not killed during the stall.

**Fix sketch**
1. Put the hard-limit in a hardware timer (`esp_timer` one-shot ISR that writes starter LOW and does not depend on the task) and/or an RTC/PWM-independent cut.
2. Use `esp_register_shutdown_handler` and `gpio_hold_en` so that panic/reset paths drive known levels; verify with a bench reset.
3. Register all output-writing tasks with TWDT.

**Verification**
- Bench (not run): block the actuator task with a busy loop during a crank; measure starter pin duration.

---

### F-02-07 - Crank hard limit is a decrement, not a monotonic deadline; drift and unbounded re-arm [P2] [VERIFIED mechanism; magnitudes INFERRED]

**Evidence**
- Decrement per loop: `actuator_safety.c:112` (`-= 20`), cut test `:105` (`<= 20`). Loop cadence: `xQueueReceive(..., tick_delay)` with `tick_delay = pdMS_TO_TICKS(20)` (`:28`, `:36`). `CONFIG_FREERTOS_HZ=1000` (`sdkconfig.defaults:26`), so 1 tick = 1 ms.
- Re-arm: a second `ACT_CMD_CRANK_START` while cranking calls `s_crank_remaining_ms = duration` and `board_set_starter(true)` again (`actuator_safety.c:64-66`); no guard on `s_cranking_active`. Repeated commands extend cranking without bound.
- Early-wake: `xQueueReceive` returns as soon as a command arrives, so that iteration consumes less than 20 ms of wall-clock but still decrements 20 (`:36`, `:112`).

**Drift quantification (INFERRED; ESP-IDF tick rounding UNVERIFIED)**
- Nominal: cut on loop 75 (`remaining` 1500 → decremented 74 times), so ≈74 × 20 ms = 1480 ms plus one loop.
- Tick quantization: a 20-tick timeout can end between 19 and 20 ms after the call (1 kHz tick). Range: 74 × 19 = 1406 ms to 74 × 20.99 ≈ 1553 ms **from quantization alone**. The 1500 ms cap is exceeded at the upper end.
- Overhead δ per loop (log, preemption, BT activity): T ≈ 74 × (20 + δ). At δ = 1 ms, T ≈ 1554 ms; at δ = 5 ms, T ≈ 1850 ms (+23%); at δ = 20 ms, T ≈ 2960 ms (~2×).
- Command floods shorten the cut (early wake), which is the safe direction for crank length.

**Consequence**
- Starter engaged up to ~2× the claimed limit under load; repeated CRANK_START unlimited. Battery/starter damage in neutral (P2); in gear, the F-02-01 hazard lasts longer.

**Fix sketch**
1. Store `deadline_us = esp_timer_get_time() + duration*1000` at start; check `esp_timer_get_time() >= deadline_us` each loop. `esp_timer` is already included in `failsafe.c:6` (unused there).
2. Reject CRANK_START while `s_cranking_active` (or make it extend only up to a cumulative cap per hour).
3. Add a cumulative crank budget (SECURITY §3.3 nonce/replay already exists in spec; not in code).

**Verification**
- Host test with a simulated clock; add a load generator to measure cut time.

---

### F-02-08 - BLE ignition path has no token or signature check; the only gate is an 18 ms RTT; no caller; scan is a stub [P1 - P0 on wiring] [VERIFIED]

**Evidence**
- `ble_keyless_start_scan()` only sets LED and a random nonce (`ble_keyless.c:20-29`); no NimBLE scan or GATT code (`firmware/main/` has no `nimble`/`ble_gap` calls; grep verified).
- `ble_keyless_verify_challenge_response()` (`ble_keyless.c:31-54`): RTT check at `:42`; comment "Kriptografik İmza / Token Teyidi" at `:49` with **no code**; `board_set_ignition(true)` at `:52`.
- Caller: none (grep verified). `SECURITY_SPECIFICATION.md:54-62` requires AES-128-GCM token with timestamp and replay window; not implemented.
- RTT measured from a caller-supplied `received_timestamp_us` (`:31`, `:39`), so the RTT is only as trustworthy as the caller.

**Failure mode + trigger**
- Once the GATT response path calls this function: any BLE device that returns any bytes within 18 ms of the nonce is accepted (`:42-53`). A relay (30-100 ms per spec, `SECURITY_SPECIFICATION.md:59`) fails the RTT check, but a local attacker who has the nonce from the air (16 bytes, sent in clear over GATT, `:53`) answers within the window.
- Also: `board_set_ignition(true)` bypasses the actuator (see F-02-05); the ignition state is not tracked.

**Consequence**
- Theft-enabling ignition from any BLE-capable device within ~18 ms latency window once wired. P1 today; P0 on wiring.

**Fix sketch**
1. Implement the signed challenge-response (HMAC/AES-GCM, timestamp ±5 s per spec) before any ignition request.
2. Route ignition through `actuator_request_ignition(true)`.
3. Require pairing with LE Secure Connections (`SECURITY_SPECIFICATION.md:66`); `sdkconfig.defaults:39` already sets `CONFIG_BT_NIMBLE_SM_SC=y` (pairing enforcement itself is not in code).

**Verification**
- Static. Proposed: replay/forgery test once a host-side challenge exists.

---

### F-02-09 - Deep sleep: PROFET_IN not forced off, no pad hold, kill released, and sleep is never entered; relay state during sleep undefined [P1 latent] [VERIFIED code; pad state UNVERIFIED]

**Evidence**
- `power_manager.c:45-48`: sets PIN_SSR_KILL, PIN_SSR_STARTER, PIN_SIREN_CTRL to 0. **Not** PIN_PROFET_IN (GPIO8) or PIN_PROFET_DEN (GPIO15). Ignition (PROFET) is therefore left in whatever state it was in.
- No `gpio_hold_en`/`gpio_deep_sleep_hold_en` anywhere (grep verified). Without a hold, output pad levels in deep sleep are not guaranteed by the firmware.
- `esp_deep_sleep_start()` at `power_manager.c:51`. Caller of `power_manager_enter_deep_sleep`: none (grep verified).
- Sleep wakeup: EXT0 on `PIN_IMU_INT1` (`power_manager.c:43`), mapped to the IMU (`:20-22`). PROJECT §4 says EXT0 = RI and EXT1 = IMU (`PROJECT.md:81-82`). Drift.
- Any wake = full reboot (deep sleep loses RAM), and `board_pins_init` drives all outputs LOW on every boot (`board_pins.c:37-45`, `main.c:105`).

**Failure mode + trigger**
- Trigger: sleep entered with ignition on (e.g., a future "park → sleep" rule that does not check `actuator_is_ignition_on()`). PROFET_IN was not written low, so ignition can remain ON during sleep with no MCU to shut it down (UNVERIFIED depending on pad default; if the pad floats LOW, ignition is off).
- Kill SSR is written LOW (released) before sleep, so the engine is not held dead during sleep.

**Relay state (answers Q6)**
- During sleep: PROFET_IN = pad default (UNVERIFIED); SSR_KILL/STARTER/SIREN = LOW (set before sleep, not held → pad default UNVERIFIED).
- After wake: reboot → `board_pins_init` drives LOW. Ignition is OFF after every wake; a running bike is cut at wake. This is a design conflict with keyless-go (INFERRED).
- Default-safe: depends on pad default; code does not guarantee it (I8).

**Consequence**
- Ignition ON during sleep with no supervision (P1 if reachable); PROJECT §4 design (1.5 s wake for BLE) would cut ignition each cycle.

**Fix sketch**
1. Require `!actuator_is_ignition_on()` before sleep; force PROFET_IN and PROFET_DEN LOW and call `gpio_hold_en` on all output pins before `esp_deep_sleep_start`.
2. Resolve the EXT0/EXT1 mapping against PROJECT §4.
3. Bench-measure pad state with a meter during sleep (UNVERIFIED).

**Verification**
- Bench: sleep with PROFET_IN high in a test build, measure IN pin voltage.

---

### F-02-10 - Emergency shutdown is latched in software with no release API; only reboot clears it; ignition re-enable does not clear kill [P2] [VERIFIED]

**Evidence**
- Latch set: `actuator_safety.c:92` (kill ON), no timeout.
- Release paths: `ACT_CMD_KILL_SSR_SET(false)` (`:81-83`), sender: none; `failsafe_cancel_soft_kill()` (`failsafe.c:77`), caller: none. Public API `actuator_safety.h:36-39` offers no release.
- `ACT_CMD_IGNITION_SET(true)` (`actuator_safety.c:38-40`) turns PROFET on with the kill still asserted: the engine remains dead while the actuator reports ignition ON.
- Reboot releases it (`board_pins.c:37`).

**Failure mode + trigger**
- Any emergency kill (e.g., false alarm) strands the owner until a power cycle; a legitimate owner cannot restart remotely or via keyless.

**Consequence**
- Operational strand; no safety hazard in the kill direction. P2.

**Fix sketch**
1. Authenticated owner-release command, with a re-arm path that requires verified speed == 0 and key presence.
2. Make `IGNITION_SET(true)` fail when kill is latched and report the reason (telemetry).

**Verification**
- Static.

---

### F-02-11 - Neutral transients: a glitch can enable a brief starter pulse in gear, bounded to ~20 ms by the in-loop check [P3] [INFERRED]

**Evidence**
- No debounce: `board_is_neutral()` is a single read (`board_pins.c:93-97`).
- Command-time check `actuator_safety.c:55` and board-level check `board_pins.c:75` (both single-shot). In-loop check `actuator_safety.c:100` runs every loop while `s_cranking_active`.
- Optocoupler response 4 µs rise / 3 µs fall typical (datasheet, UNVERIFIED on the part) - a LED-side glitch is transferred essentially instantly.

**Failure mode + trigger**
- A LOW glitch sampled at `actuator_safety.c:55` while the bike is in gear (bounce, wet connector) lets the crank start. The next loop (≤20 ms later) reads HIGH (in gear) and aborts (`:100-104`, and `board_pins.c:77-78` drives the starter LOW).
- Exposure: ≈20-40 ms of starter engagement. Only a steady in-gear state followed by a glitch at command time reaches this path.

**Consequence**
- Brief starter pulse in gear: small but non-zero motion risk (INFERRED: a 20-40 ms starter pulse drives the pinion briefly; magnitude UNVERIFIED). Not a sustained hazard, because the in-loop check aborts.
- Important: a **sustained** false-neutral (open line, F-02-01) defeats this bounded abort, because the sense line reads LOW for the whole crank.

**Fix sketch**
1. Require N consecutive neutral samples (e.g., 3 × 20 ms) at command time (the spec does not require it; it reduces chatter).
2. Keep the in-loop abort; fix F-02-01 for the sustained case.

**Verification**
- Host test with a glitch injection on the GPIO read.

---

### F-02-12 - failsafe_cancel_soft_kill() vTaskDelete()s a live task from another context; stale writes and orphan tasks possible; trigger has a TOCTOU [P2] [VERIFIED code; SMP semantics UNVERIFIED]

**Evidence**
- Cancel: `failsafe.c:70-80`. Calls `vTaskDelete(soft_kill_task_handle)` (`:73`), then writes siren/kill (`:76-77`). Worker is pinned to Core 0 (`failsafe.c:65`); cancel's caller context is not constrained (no caller in tree; grep verified).
- Trigger: `failsafe.c:57` checks `soft_kill_task_handle == NULL` then creates the task (`:58-66`) without a lock. Two concurrent triggers can create two tasks; only the last handle is stored (`:64`), so cancel can delete only one.
- Worker never clears its own handle; it exits only via `vTaskDelete(NULL)` (`:46`) which is unreachable in practice because state never leaves LOCKOUT (`:39` loop). After any self-delete the stale handle blocks future triggers (`:57`).
- `current_kill_state` and `soft_kill_task_handle` are written by multiple contexts without synchronisation (`failsafe.c:9-10`).

**Failure mode + trigger**
- Cancel from Core 1 while the worker is between `board_set_kill_ssr(false)` at `:22` and `board_set_kill_ssr(true)` at `:20`: FreeRTOS SMP may let the worker execute its next GPIO write after cancel's `:76-77` (UNVERIFIED for ESP-IDF). Final kill/siren state becomes non-deterministic.
- GPIO writes are single register writes, so no tearing; the hazard is ordering and stale execution.
- Two triggers (e.g., BLE + GNSS geofence) → two workers; cancel leaves one running, which keeps siren and kill asserted forever (`:38-44`).

**Consequence**
- Kill asserted or siren asserted with state IDLE (no alarm record; engine dead if kill ON). Kill-leaning (fail-safe for the engine, unsafe for the rider if at speed). P2 because no caller exists and the outcome is in the direction of "engine stopped".

**Fix sketch**
1. Replace `vTaskDelete` with a cancel flag/queue message the worker polls; the worker deletes itself.
2. Protect handle and state with a critical section or a mutex; make trigger idempotent.
3. Fold soft-kill into the single owner task (F-02-05).

**Verification**
- Host or Renode test with two triggers and a cancel from the other core.

---

### F-02-13 - Theft alarm / tamper sensing is not implemented: LIS3DH unconfigured, INT1 read as an unconfigured GPIO [P1] [VERIFIED]

**Evidence**
- `PROJECT.md:14-16` claims instant interrupt-driven detection of lifting/tamper.
- `sensors_imu_read_accel()` returns constants plus a raw GPIO read of `PIN_IMU_INT1` (`sensors_imu.c:37-40`). `PIN_IMU_INT1` (`board_pins.h:33`) is not in `board_pins_init`'s input list (`board_pins.c:48-54`), so it has reset-default pad configuration (UNVERIFIED default pull).
- `sensors_imu_configure_wakeup_threshold()` only logs (`sensors_imu.c:44-47`); no I2C write to LIS3DH registers exists (grep verified).
- `main.c:28-34` toggles the alarm LED from this value. `main.c:29` logs "Verifying vehicle authorization" but nothing happens after.
- Siren is driven only by the soft-kill task (`failsafe.c:29`, `:40-42`), which is never triggered. So with no trigger, the bike has **no sounded alarm on movement**.

**Failure mode + trigger**
- Any tamper or lift event is not detected (or is detected only by a floating pin). Siren does not sound. The bike is not alarmed in production.

**Consequence**
- Theft-enabling: the primary anti-theft promise in PROJECT §2.1 (`PROJECT.md:14-16`) is absent. Release-blocking (P1). Not P0 because the bike is not "armed" by any state machine in the tree.

**Fix sketch**
1. Configure LIS3DH over I2C (CTRL_REG, threshold, INT1 latch); configure `PIN_IMU_INT1` as input with explicit pull.
2. Add an ARMED state; raise a siren event on motion while armed (through the owner task).

**Verification**
- Bench with the LIS3DH on the I2C bus.

---

### F-02-14 - Power/sleep, fail-safe, and cancel code paths are dead code; the `failsafe_can_crank_starter` gate is never consulted [P2] [VERIFIED]

**Evidence**
- `failsafe_can_crank_starter()` (`failsafe.c:87-93`) would block cranking during soft-kill; callers: none (grep verified). The actuator's crank path consults only ignition and neutral (`actuator_safety.c:50`, `:55`), so CRANK_START is accepted during stages 1-2 (ignition still ON, see F-02-05 item 5).

**Consequence**
- A remote crank during the soft-kill window would re-engage the starter while the kill pulses; low risk alone (engine running under pulses), but it is an unenforced invariant. P2.

**Fix sketch**
- Consult `failsafe_get_kill_state()` in the owner's crank path, or fold into the owner state machine.

---

### F-02-15 - OTA rollback is confirmed before any self-test; a boot-but-mis-actuating build is locked in [P2] [VERIFIED]

**Evidence**
- `main.c:127-128`: `verify_and_confirm_ota_rollback()` runs immediately after `modem_init` (`:125`), before actuator, IMU, or BLE functional checks. The README promises confirmation only after the new version has completed "tüm donanım testlerini (GPIO, IMU, Modem, Aktüatörler) başarıyla tamamlayıp" (`firmware/README.md:48`) - no such self-test exists in `main.c`.

**Consequence**
- A build that boots but drives actuators wrongly is marked valid; rollback protection does not catch safety regressions. P2.

**Fix sketch**
- Move confirmation to after a self-test that exercises the owner task (ignition/starter/kill echoes, neutral read, IMU alive).

---

### F-02-16 - `actuator_send_cmd` is documented as callable from interrupts, but uses a blocking `xQueueSend` with timeout [P2] [INFERRED]

**Evidence**
- Header: "Core 1 veya Kesmelerden çağrılabilir" (`actuator_safety.h:35`).
- Implementation: `xQueueSend(s_actuator_queue, cmd, pdMS_TO_TICKS(50))` (`actuator_safety.c:152`), not `xQueueSendFromISR`. Standard FreeRTOS forbids blocking/non-ISR calls from ISR context (UNVERIFIED for ESP-IDF version; standard behaviour).

**Consequence**
- A future ISR caller (e.g., an IMU interrupt wired to actuation) asserts/crashes; panic-reboot during a crank leaves the starter in last state until reset (F-02-06). P2 now.

**Fix sketch**
- Provide `actuator_send_cmd_from_isr` using `xQueueSendFromISR`; or fix the header.

---

### F-02-17 - Documentation drift and contradictions (P3, one P2 contradiction) [P2/P3] [VERIFIED]

| # | Item | Evidence | Rating |
|---|---|---|---|
| a | `PROJECT.md:157-159` (remote kill **deferred** until V=0) contradicts `SECURITY_SPECIFICATION.md:134-135` and `TARGET_MARKET` §5 (soft-kill **while moving**) | three sources | **P2** (the spec must pick one before code can be judged) |
| b | `firmware/README.md:38` TWDT "sets relays to 0" vs. `actuator_safety.c` and `failsafe.c` have no such path (I5) | `README:38` | P1 (already F-02-06) |
| c | `PROJECT.md:80-82` EXT0=RI, EXT1=IMU vs `power_manager.c:20-22, :43` EXT0=IMU | | P3 |
| d | `PCB_SPECIFICATION.md:116` R4 pull-up on SENSE_NEUTRAL vs netlist R4=ESP_EN (`generate_kicad_pcb.py:1207`) | | P2 (BOM/doc mismatch) |
| e | `PCB_SPECIFICATION.md:123` R14 100 kΩ vs netlist R14 10 kΩ (`generate_kicad_pcb.py:1254`, `generate_kicad_sch.py:711`) | | P2 (changes the LOW level and the GPIO LOW margin; F-02-01) |
| f | `board_pins.c:51` GPIO12 internal pull-up fights the 10 kΩ external pulldown (netlist) → LOW level ≈ 3.3 V × 10k/(10k + ~45k) ≈ 0.6 V (INFERRED; internal pull-up value UNVERIFIED) - marginal against ESP32-S3 VIL threshold (UNVERIFIED) | | P2 |
| g | `sim/wokwi/diagram.json:64-67, 91` models neutral as a pushbutton on IO12, not an opto-isolated open-collector: the simulator cannot reproduce F-02-01 | | P3 |
| h | `firmware/README.md:40` says 1500 ms is "mutlak" (absolute) while the code is a decrement (F-02-07) | | P3 |
| i | `firmware/README.md:37` ("Yüksek Öncelik") and `sim/README.md` §2.1 claim isolation of U10/U11/U12 from other tasks; `failsafe.c:20-36` writes those outputs directly (F-02-05) | | P2 |
| j | `main.c:110` says "Max Priority" for the actuator task; actuator is at -2 (`actuator_safety.c:136`), soft-kill at -1 is higher (`failsafe.c:63`) | | P3 |

---

## Open Questions

1. **Spec conflict on remote kill:** should a theft kill execute while moving (SECURITY §5.1, TARGET §5) or be deferred until stopped (PROJECT §6)? The code implements neither. This decides F-02-02 and F-02-04.
2. **Neutral switch convention** on the target bikes (closed-in-neutral or closed-in-gear)? Needed to confirm F-02-01 trigger B (UNVERIFIED).
3. **Is there an electrical series neutral interlock in the intended design?** SECURITY §5.2 says yes; the netlist says no. Which is authoritative?
4. **Speed source:** will GNSS CGNSINF or CAN (ISO 19689) be the V=0 source? Which one is the trust anchor, and what happens when the fix is stale?
5. **Pad state:** what are GPIO3/8/9/46 levels during reset and deep sleep on the actual silicon? Needed for I1, I5, F-02-09 (UNVERIFIED; confirm in the ESP32-S3 TRM).
6. **BT controller task priority on Core 0** relative to the actuator task (-2). Determines the crank-timing drift in F-02-07 and TWDT behaviour in F-02-06.
7. **Is a hardware-only kill (MCU-independent) intended?** Currently the kill SSR is NO, so an MCU death releases the kill; PROFET-off is the only default cut (INFERRED consequence).
8. **Does `failsafe_trigger_soft_kill` run from one context only?** Determines whether F-02-12's TOCTOU is reachable.

## Suggested Jobs

1. **Fix-first (before any remote-command wiring):** F-02-01 (neutral: invert to fail-safe, add series interlock), F-02-02/F-02-03 (speed source + speed gating; sim default non-zero speed), F-02-08 (signed challenge before ignition).
2. **Single-owner refactor:** F-02-05, F-02-12, F-02-14, F-02-16 - all writes through the actuator task; latched emergency flag; cancel as a message; ISR-safe send.
3. **Timing:** F-02-07 - monotonic deadline via `esp_timer`; cumulative crank budget; reject re-arm.
4. **Watchdog & reset:** F-02-06 - hardware-timed starter cut, `gpio_hold_en`, shutdown handler, register all output tasks with TWDT.
5. **Sleep:** F-02-09 - force PROFET low and hold before `esp_deep_sleep_start`; check ignition off first.
6. **Theft sensing:** F-02-13 - configure LIS3DH; armed state; siren via owner.
7. **Diagnostics:** F-02-10 (owner release with authentication), PROFET IS ADC read and fault tracking (table below), starter/kill SSR fault detection.
8. **Docs/BOM reconciliation (F-02-17):** R4/R14 values, EXT0/EXT1, remote-kill semantics, ownership/isolation wording, TWDT claim.

### F-02-18 - PROFET IS current sense never read; stuck-on, bypass, stuck-SSR, and harness faults are invisible [P1] [VERIFIED absence; consequences INFERRED]

**Evidence**
- `PIN_PROFET_IS` = GPIO10, "ADC1_CHANNEL_9" (`board_pins.h:26`). Grep over `firmware/`: no `adc_`/`esp_adc` calls; only the define. Verified.
- Ignition state reported to telemetry is the commanded state, `actuator_is_ignition_on()` (`main.c:63`, backed by `actuator_safety.c:39`), not a measurement.
- `board_set_ignition()` also drives `PROFET_DEN` (`board_pins.c:68`) with no readback.
- Netlist: PROFET is in series on the ignition path between `J1` pins 3 (`IGNITION_IN`) and 4 (`IGNITION_OUT`) (`generate_kicad_pcb.py:1270-1272` and `U10` pins `:1242-1246`). A jumper across `J1.3`-`J1.4` bypasses the PROFET entirely. No sense exists on `IGNITION_OUT` (ADC lines are battery only: `generate_kicad_pcb.py:1256-1257`).
- SSR U11 (starter) and U12 (kill) have no output-state sense at all.

| Failure | Physical state | Visible to MCU today? | Consequence |
|---|---|---|---|
| PROFET stuck closed (ON while IN=0) | Ignition live, firmware says OFF | **No** | Bike rideable in "lockout"; stage 3 believes it is off (F-02-05 item 5) |
| PROFET fault-latched (overcurrent/short, BTS7002 protection) | Ignition dead | **No** (IS/DEN fault flag unread) | Silent no-start; customer-facing (P2) |
| Short to GND on IGN_OUT | Overcurrent in PROFET | **No** | Thermal stress; invisible (INFERRED: depends on BTS7002 protection behaviour, UNVERIFIED) |
| Jumper across J1.3–J1.4 (bypass) | Ignition live, PROFET bypassed; IS reads zero | **No** | The primary theft-by-bypass vector (`TARGET_MARKET` §1, `PROJECT.md:6`) |
| Starter SSR U11 stuck closed (output short) | Starter energised continuously, **even in gear** with no command | **No** (no current sense; `actuator_safety.c` timer only governs commands) | F-02-01 hazard without any MCU fault; battery drain (P1 hazard in gear) |
| Kill SSR U12 stuck closed | Ignition shorted to ground: engine dead at any moment, including at speed | **No** | Hard kill at speed without command (P1, INFERRED consequence) |
| Harness cut on load side | Ignition/starter open | **No** | Silent no-start (P3) |
| Siren FET Q5 stuck on | Siren sounds | **No** | Nuisance; battery drain (P3) |

**Failure mode + trigger**
- Trigger for bypass: physical access to the harness connector `J1` (the thief's route). Trigger for stuck SSR: component failure (UNVERIFIED rate).

**Fix sketch**
1. Read `PROFET_IS` through ADC1 (`adc_oneshot`) when IN is high; compare to expected load current; treat near-zero IS with IN low as "PROFET stuck or bypass" only if a bike-side IGN sense exists (add a voltage sense on `IGNITION_OUT` through a divider).
2. Add a bike-side ignition sense (divider on `IGNITION_OUT`) so the MCU can see the output after the PROFET, detecting bypass.
3. Add starter and kill feedback (sense across SSR output via a divider or a current shunt; or require the crank to be followed by a measured RPM/starter-current pulse).
4. Report fault flags in telemetry (`main.c:60-64` currently prints commanded state).

**Verification**
- Bench: energize the PROFET with IN low (stuck test), jumper J1.3–J1.4, and measure with the new sense; UNVERIFIED until built.

---

## Answers to the spec's analysis questions (index)

- Q1 invariants → proof table above (I1-I10).
- Q2 ownership race → F-02-05 (priority -1 vs -2; sequence; consequence).
- Q3 soft-kill at 60 km/h → F-02-02 (50 m in stage 1, 2 s siren at speed, hard cut at ~83 m / t≈5 s); top design defect, rated P1 today, P0 on wiring.
- Q4 speed source → F-02-03 (none; hard-coded 0 in `modem.c:88`; IMU constants).
- Q5 neutral interlock → F-02-01 (no debounce; open→NEUTRAL; no electrical series path); transients bounded to ~20 ms in F-02-11.
- Q6 crank hard limit → F-02-07 (decrement, not monotonic; quantified drift; re-arm unbounded); stall path F-02-06.
- Q7 deep sleep → F-02-09 (PROFET_IN not forced; no hold; never called; pad state UNVERIFIED).
- Q8 emergency shutdown → F-02-10 (latched, no release API, reboot only; kill left asserted).
- Q9 cancel vTaskDelete → F-02-12 (cross-context delete; stale write; TOCTOU; orphan).
- Q10 PROFET IS → F-02-18 (invisible failures table).
- Q11 cross-check → F-02-17 and per-finding citations to SECURITY §5, PROJECT §2, §4, §6.

## Summary of severities

- **P1 (latent, blocks release; P0 on wiring):** F-02-01 neutral, F-02-02 soft-kill speed-blind, F-02-03 no speed source, F-02-04 immediate remote kill / lost emergency, F-02-05 ownership race, F-02-06 TWDT claim false, F-02-08 BLE ignition without token, F-02-09 deep sleep, F-02-13 no theft alarm, F-02-18 PROFET IS unread.
- **P2:** F-02-07 crank drift/re-arm, F-02-10 latch no release, F-02-12 cancel/TOCTOU, F-02-14 dead gate, F-02-15 OTA confirm, F-02-16 ISR-unsafe send, F-02-17 (a, d, e, f, i).
- **P3:** F-02-11 transient neutral, F-02-17 (c, g, h, j).
- **P0:** none rated in the current tree (no reachable entry point). Every P1 above becomes P0 the moment the corresponding remote, BLE, or geofence trigger is wired.
