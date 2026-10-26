# 05 - Hardware Pinmap & Electrical Cross-Check

## Summary

- **Neutral interlock input is inverted in the netlist (P0; electrical part UNVERIFIED).** Firmware treats GPIO12 LOW as "in neutral" (`firmware/main/board_pins.c:95-96`). The generator ties the opto collector (pin 4) to +3V3 and pulls the output down with R14 10k to GND (`hardware/pcb/generate_kicad_sch.py:709-712`). With the opto off (switch open = in gear), GPIO12 reads LOW, so the firmware reports NEUTRAL. The starter interlock fails open.
- **Motion alarm path is dead (P0, theft-enabling).** `sensors_imu_read_accel()` reads GPIO4 with `gpio_get_level` (`firmware/main/sensors_imu.c:40`). GPIO4 is never configured as an input, and the LIS3DH is never configured to drive INT1 (no register access anywhere in `firmware/`). Per ESP-IDF docs (UNVERIFIED), an unconfigured pad reads 0, so `motion_detected` is constant false.
- **GSM LED pin conflicts three ways.** Firmware uses GPIO46 (`board_pins.h:47`). The PCB spec says GPIO46 (`hardware/pcb/PCB_SPECIFICATION.md:163`). The generated netlist puts the LED on GPIO45 (`generate_kicad_sch.py:577`) with GPIO46 NC (`generate_kicad_sch.py:566`). Both are strapping pins, and GPIO45's net is shared with SIM808 NETLIGHT (`generate_kicad_sch.py:653`).
- **Modem STATUS is wired to the wrong pin, and PWRKEY polarity is inverted.** Firmware reads GPIO21 as STATUS (`board_pins.h:43`, `modem.c:60`). The netlist puts RI on GPIO21 and STATUS on GPIO40 (`generate_kicad_sch.py:574, 584`). Firmware drives PWRKEY HIGH to press (`modem.c:51-53`), but the SIM808 key is active-LOW (UNVERIFIED).
- **PROFET IS has no clamp.** IS goes straight to GPIO10 through R10 1.2 kΩ (`generate_kicad_sch.py:681, 569, 694-695`). Using Infineon datasheet typicals (UNVERIFIED), fault current gives roughly 5-12 V at IS, which exceeds the ESP32-S3 pad rating. The ADC that would read the pin is never initialised.
- **Deep sleep is not implemented.** `power_manager_enter_deep_sleep()` has no callers (`firmware/main/power_manager.c:32`), and there is no hold or RTC-isolate code. PROFET_IN (GPIO8) is not forced low before sleep and has no external pull-down in the netlist.
- **Strapping is only partly handled.** GPIO3 (kill SSR) has no pull network and floats until `board_pins_init`. GPIO45 is LED-driven on the PCB and may latch VDD_SPI at 1.8 V (datasheet-dependent, UNVERIFIED).

---

## Scope & Method

**Files read (repo, read-only):** `firmware/main/board_pins.h`, `board_pins.c`, `sensors_imu.c/.h`, `modem.c`, `power_manager.c/.h`, `main.c`, `actuator_safety.c`, `failsafe.c`, `ble_keyless.c`, `firmware/main/CMakeLists.txt`, `firmware/CMakeLists.txt`, `firmware/platformio.ini`, `firmware/sdkconfig.defaults`, `firmware/partitions.csv`, `firmware/README.md`, `PROJECT.md`, `hardware/pcb/PCB_SPECIFICATION.md`, `hardware/pcb/generate_kicad_sch.py`, `hardware/production/automoto_bom_jlcpcb.csv`, `sim/wokwi/diagram.json`, `sim/README.md`, `sim/renode/automoto.repl`. `hardware/pcb/automoto.kicad_sch` was only grepped for net labels.

**Not in repo (all datasheet facts are UNVERIFIED):**
- BTS7002-1EPP, LTV-356T, SIM808 hardware design, LIS3DH, ESP32-S3 datasheet, ESP32-S3-WROOM-1 N16R8 module datasheet.
- External facts were pulled from web search and docs.espressif.com in this session. They are cited as UNVERIFIED and need a pinned datasheet to confirm.

**Not run:**
- `kicad-cli` ERC/DRC, ESP-IDF, PlatformIO. No build or flash result is claimed.
- No electrical measurement is claimed. Every voltage or current figure is a calculation from datasheet typicals and is UNVERIFIED.

**Method:** Pins from `board_pins.h` were cross-matched to the README, PCB spec, the KiCad generator's pin and net tables, the BOM, and the Wokwi diagram. Each define's set/get path was traced for polarity. ESP32-S3 restrictions were checked against Espressif's GPIO and strapping tables.

---

## Findings

### F-05-01 - Neutral interlock input is inverted in the netlist; in-gear reads as NEUTRAL (fail-open) [P0] [UNVERIFIED]

**Evidence (firmware, VERIFIED):**
- `firmware/main/board_pins.h:30`: `PIN_SENSE_NEUTRAL GPIO12 // Active LOW`.
- `firmware/main/board_pins.c:48-52`: input with internal pull-up.
- `firmware/main/board_pins.c:93-96`: `board_is_neutral()` returns `gpio_get_level(PIN_SENSE_NEUTRAL) == 0`. LOW means neutral.
- `firmware/main/actuator_safety.c:55` and `:100`, `firmware/main/failsafe.c:92`: this function is the crank interlock.

**Evidence (netlist generator, VERIFIED as generator content):**
- `hardware/pcb/generate_kicad_sch.py:709-710`: U9 (LTV-356T), pin 1 = NEUTRAL_ANODE, pin 2 = NEUTRAL_SENSE, **pin 4 = +3V3, pin 3 = NEUTRAL_OUT**.
- `generate_kicad_sch.py:711-712`: R14 10k from NEUTRAL_OUT to GND.
- `generate_kicad_sch.py:707-708`: R13 4.7k from +12V_IN to the opto LED anode.
- `generate_kicad_sch.py:571` and `:762`: NEUTRAL_OUT goes to ESP pin 20 (IO12); NEUTRAL_SENSE goes to Molex J1 pin 8 (neutral switch wire).
- No pull-up on NEUTRAL_OUT. R4 is the EN pull-up (`generate_kicad_sch.py:596-597`); the spec's "R4 neutral pull-up" (`PCB_SPECIFICATION.md:116`) is not in the netlist.

**Analysis:**
- The firmware pull-up is about 45 kΩ (UNVERIFIED). Against R14 10k it forms a divider: with the opto off, the pin sits near 0.2 × VDD and reads LOW, which firmware calls NEUTRAL.
- "Active LOW" requires the opto collector (pin 4) at GND with the emitter (pin 3) to the GPIO and a pull-up. The netlist ties pin 4 to +3V3, which makes the output active-HIGH.
- Assumed LTV-356T pinout (UNVERIFIED): 1 anode, 2 cathode, 3 emitter, 4 collector. Under that pinout the output follows the LED: LED on gives HIGH, LED off gives LOW.
- Assumed neutral switch wiring (UNVERIFIED): the switch shorts NEUTRAL_SENSE to GND in neutral, so the LED conducts in neutral.
- `PROJECT.md:158` requires the neutral interlock to be connected "donanımsal veya mantıksal olarak seri" (hardware or logically in series). The netlist makes it a single GPIO read with no hardware series path.

**Failure mode / trigger:** Bike in gear, switch open. The opto is off, GPIO12 reads LOW, `board_is_neutral()` returns true, so `board_set_starter(true)` and `ACT_CMD_CRANK_START` pass the interlock. The starter fires in gear. An open or disconnected neutral wire gives the same result.

**Consequence:** Starter-in-gear is safety-of-life. It also defeats the stated anti-theft and anti-gasp interlock.

**Fix sketch:**
1. Confirm the LTV-356T pinout and the neutral switch wiring from the BOM datasheet and the harness.
2. Choose one polarity and match the netlist. If firmware keeps "LOW = neutral", tie pin 4 to GND and pull NEUTRAL_OUT up to +3V3. Then an open wire or open opto reads HIGH = IN GEAR, which is fail-safe.
3. Add a hardware-series neutral path so the starter SSR cannot conduct unless the switch is closed (`PROJECT.md:158`).
4. Firmware: treat an ambiguous or unchanging reading as "not neutral" and refuse crank.

**Verification:** ERC plus a netlist walk from J1 pin 8 to GPIO12 using the real LTV-356T symbol. Bench test with switch open, closed, and disconnected (not run here).

---

### F-05-02 - Motion/IMU interrupt pin GPIO4 is read but never configured; LIS3DH is never configured [P0] [VERIFIED]

**Evidence:**
- `firmware/main/sensors_imu.c:40`: `out_data->motion_detected = (gpio_get_level(PIN_IMU_INT1) == 1);`.
- `firmware/main/board_pins.c:48-52`: the input config covers only `PIN_SENSE_NEUTRAL` and `PIN_MODEM_STATUS`. GPIO4 and GPIO5 are not configured.
- `firmware/main/sensors_imu.c:15-27`: I2C master is installed, but no LIS3DH register is written. `sensors_imu_configure_wakeup_threshold` (`sensors_imu.c:44-47`) only logs.
- `grep` over `firmware/`: no `CTRL_REG`, no `WHO_AM_I`, no I2C read or write call.
- `firmware/main/main.c:28-34`: alarm LED follows `motion_detected`.

**Analysis (what the read returns):**
- ESP-IDF GPIO docs (UNVERIFIED, docs.espressif.com, fetched this session): "If the pad is not configured for input (or input and output) the returned value is always 0." The ESP32-S3 default-configuration table gives GPIO4 no input-enable at reset (UNVERIFIED).
- So `gpio_get_level(GPIO4)` returns 0 on every call and `motion_detected` is constant false.
- Even with the pin configured, the LIS3DH must drive INT1. Its INT1 is push-pull forced LOW by default (LIS3DH datasheet, UNVERIFIED web excerpt), so without configuration it never asserts.

**Failure mode / trigger:** Any motion or tamper event. The sensor never asserts and the MCU never sees it.

**Consequence:** The theft alarm (siren and LED) cannot fire from the IMU. Theft-enabling.

**Fix sketch:**
1. Implement LIS3DH init over I2C: WHO_AM_I check, CTRL_REG1 (ODR and axes), CTRL_REG3 (INT1 routing), INT1_CFG and INT1_THS, latch or pulse mode.
2. Configure GPIO4 as an input with the pull the board requires before reading it.
3. Add a polled fallback (`INT1_SRC` or `OUT_X/Y/Z` deltas) so the alarm does not depend on one pin.
4. Remove the constant x/y/z values (`sensors_imu.c:37-39`) or label them as simulated.

**Verification:** Hardware-in-loop: shake the board, confirm an INT edge on GPIO4 and a `motion_detected` transition in the log (not run here).

---

### F-05-03 - GSM LED: firmware GPIO46, PCB GPIO45 (GPIO46 is NC), with a NETLIGHT net collision [P1] [VERIFIED; strap effect UNVERIFIED]

**Evidence:**
- Firmware: `firmware/main/board_pins.h:47` `PIN_LED_GSM GPIO_NUM_46`. Driven at `firmware/main/main.c:52-54`.
- PCB spec: `hardware/pcb/PCB_SPECIFICATION.md:163` "Pin 16 IO46 LED_GSM".
- Generator: `generate_kicad_sch.py:279` lists symbol pin 16 as `IO46`, but `generate_kicad_sch.py:566` assigns pin 16 to **NC**. `generate_kicad_sch.py:291` lists pin 26 as `IO45_LED_GSM`, and `generate_kicad_sch.py:577` assigns **LED_GSM_DRV** to pin 26. The PCB LED is on GPIO45.
- SIM808 side: `generate_kicad_sch.py:653` assigns **LED_GSM_DRV** to SIM808 pin 52 (NETLIGHT on the symbol). ESP and SIM808 are both drivers on this net.
- Wokwi: `sim/wokwi/diagram.json:84` wires `esp:46` to the green LED. The simulator agrees with firmware, not the PCB.

**Analysis:**
- GPIO46 and GPIO45 are both strapping pins (see F-05-06).
- Two push-pull drivers on one net is bus contention. R7 (330 Ω) limits the current, but the state is ambiguous.
- Firmware drives GPIO46, which is unconnected on the board. The firmware GSM LED never lights. The real LED is driven by GPIO45 (never set by firmware) and by NETLIGHT, so the "GSM status" LED reflects the modem's own NETLIGHT, not `modem_is_alive()`.

**Failure mode / trigger:** Normal operation. The status indicator is wrong on the production board.

**Consequence:** Misleading user indicator. Couples a strapping pin to a modem output (F-05-06).

**Fix sketch:**
1. Move the GSM LED to a non-strapping digital GPIO that is free in the netlist (GPIO47 and 48 are in use). Update `board_pins.h`, README, Wokwi, and the generator together.
2. Remove the NETLIGHT connection from the ESP LED driver net, or drop NETLIGHT and drive the LED only from the ESP.

**Verification:** Netlist diff for the LED net; confirm the ESP pin is the only driver (not run here).

---

### F-05-04 - Modem STATUS: firmware reads GPIO21 but the netlist connects GPIO21 to RI [P1] [VERIFIED]

**Evidence:**
- Firmware: `firmware/main/board_pins.h:43` `PIN_MODEM_STATUS GPIO21`, read in `firmware/main/modem.c:60`: `gpio_get_level(PIN_MODEM_STATUS) == 1` means alive.
- PCB spec: `PCB_SPECIFICATION.md:168` "Pin 23 IO21 MODEM_STATUS"; `:184` says SIM808 pin 52 is STATUS.
- Generator: `generate_kicad_sch.py:574` assigns GPIO21 (pin 23) to **GSM_RI**; SIM808 pin 4 is RI (`generate_kicad_sch.py:640`, symbol `:315`). `generate_kicad_sch.py:584` assigns **GSM_STATUS** to GPIO40 (pin 33); SIM808 pin 66 is STATUS (`generate_kicad_sch.py:658`).
- `firmware/README.md:84` says "GPIO 21, 38 STATUS, PWRKEY".

**Analysis:**
- Three sources disagree on the SIM808 STATUS pin number (52 vs 66). The SIMCom datasheet is the arbiter (UNVERIFIED).
- Whatever the pin number, the ESP reads RI on GPIO21 and never reads STATUS. RI is normally idle-HIGH (UNVERIFIED), so `modem_is_alive()` probably returns true whether the modem is powered or not. That disables the recovery in `main.c:51-56`.

**Failure mode / trigger:** Modem fails to power on or drops. The liveness check still reports "alive", so no power cycle occurs.

**Consequence:** No telemetry, no remote start, and no alarm over the network. The failure is silent.

**Fix sketch:**
1. Rewire the netlist: GPIO21 to STATUS, and use a different pin for RI if it is needed for wake (see F-05-09).
2. `modem_is_alive()` should check STATUS and confirm with an AT command (`AT`) under a timeout.

**Verification:** Netlist check of GPIO21 and GPIO40; SIM808 pin table for STATUS (not run here).

---

### F-05-05 - PWRKEY drive polarity inverted versus SIM808; series resistor missing in netlist [P1] [VERIFIED firmware; UNVERIFIED datasheet]

**Evidence:**
- `firmware/main/board_pins.h:44`: GPIO38 is "Modem Açma/Kapama Pals Çıkışı" (power on/off pulse output). No polarity given.
- `firmware/main/modem.c:50-55`: `modem_power_cycle()` drives PWRKEY **HIGH for 1.2 s**, then **LOW for 2 s**.
- `firmware/main/board_pins.c:42`: PWRKEY is driven LOW at boot.
- SIM808 hardware design (UNVERIFIED web excerpt): "PWRKEY should be pulled low at least 1 second and then released to power on/off the module", "internally pulled up to VBAT".
- `PCB_SPECIFICATION.md:182` says PWRKEY has an R19 4.7 kΩ series resistor. The generator has none: `generate_kicad_sch.py:638` puts GSM_PWRKEY directly on SIM808 pin 1, and R19 is the SCL pull-up (`generate_kicad_sch.py:739`). The BOM describes R19 as a PWRKEY series resistor (`automoto_bom_jlcpcb.csv:27`). BOM and generator disagree.

**Analysis:**
- Firmware uses HIGH to press. For SIM808, LOW is press and HIGH is released.
- Trace: `board_pins_init` puts the pin LOW at boot (`board_pins.c:42`). `modem_init` sees the modem not alive and calls `modem_power_cycle`, which first releases (HIGH) for 1.2 s. The following LOW phase is a 2 s press, and the release comes at the start of the next call. Whether the modem actually toggles depends on call timing (UNVERIFIED).
- The pulldown on GPIO38 (`board_pins.c:27`) holds the idle level LOW, which is the pressed level for SIM808 (see F-05-14).

**Failure mode / trigger:** Modem never powers on, or toggles at unexpected times depending on call ordering.

**Consequence:** Telemetry and remote start are unreliable. Blocks production.

**Fix sketch:**
1. Define PWRKEY as active-LOW in `board_pins.h`. Idle HIGH (released). Press = LOW for about 1.5 s, then release.
2. Remove the pulldown on GPIO38. Use the SIM808 internal pull-up or an explicit board pull-up.
3. Add the series resistor or transistor from the SIMCom reference circuit. Reconcile R19 across spec, BOM, and generator.

**Verification:** Scope on PWRKEY during power-on and power-off sequence (not run here).

---

### F-05-06 - Strapping pins GPIO45 and GPIO46: LED load can change VDD_SPI and boot mode [P1] [UNVERIFIED]

**Evidence:**
- Strapping pins (ESP32-S3 datasheet, UNVERIFIED web excerpt): GPIO0, GPIO3, GPIO45, GPIO46. GPIO0 and GPIO46 set boot mode. GPIO45 sets VDD_SPI voltage when EFUSE_VDD_SPI_FORCE=0. GPIO46 controls ROM message printing. GPIO3 selects JTAG source only when EFUSE_STRAP_JTAG_SEL=1. Defaults: GPIO0 pulled up; GPIO3 floating; GPIO45 and GPIO46 pulled down.
- Invalid combination: GPIO46=1 with GPIO0=0 (datasheet note 1).
- PCB: GPIO45 drives LED_GSM_DRV (`generate_kicad_sch.py:577`), also driven by NETLIGHT (`generate_kicad_sch.py:653`).
- Firmware: GPIO46 is driven HIGH by `main.c:52`.
- `board_pins.c:27` applies pulldown after init. It cannot affect latches that were sampled at reset (datasheet excerpt, UNVERIFIED).

**Analysis:**
- Power-on and brownout reset sample straps. Software reset (`esp_restart`, watchdog panic) is not in the datasheet's list of latch-sampling resets (UNVERIFIED), so the main exposure is hardware reset.
- If NETLIGHT is high at hardware reset, GPIO45 may latch 1, which sets VDD_SPI to 1.8 V when EFUSE_VDD_SPI_FORCE=0. The datasheet warns that 3.3 V flash or PSRAM needs 3.3 V VDD_SPI. Whether this module's devices need 3.3 V depends on the module datasheet (UNVERIFIED).
- Holding BOOT (GPIO0 low) while GPIO46 latches 1 gives the invalid combination.
- LED path: 330 Ω to an LED to GND. Whether the pin reads as logic 1 at the strap sampler is marginal (UNVERIFIED).

**Failure mode / trigger:** Hardware reset while the modem is powered and NETLIGHT is high; or reset while SW2 (BOOT) is held.

**Consequence:** Boot failure or flash corruption at 1.8 V VDD_SPI. Unexpected download mode if BOOT is held.

**Fix sketch:**
1. Move the GSM LED off GPIO45 and GPIO46 (F-05-03).
2. Add a 10 kΩ pull-down on GPIO45 so the strap defaults to 0 if NETLIGHT is ever on the net.
3. Confirm EFUSE_VDD_SPI_FORCE and the module's VDD_SPI requirement before production.

**Verification:** eFuse dump on a sample module; module datasheet for VDD_SPI (not run here).

---

### F-05-07 - PROFET IS (GPIO10) can reach several volts; ADC not initialised; no clamp on the pin [P1] [UNVERIFIED]

**Evidence:**
- Firmware: `firmware/main/board_pins.h:26` `PIN_PROFET_IS GPIO_NUM_10 // ADC1_CHANNEL_9`. README `firmware/README.md:80` "ADC Algılama".
- No ADC code anywhere in `firmware/` (grep for `adc`, `ADC`, `esp_adc` returns nothing). `firmware/main/CMakeLists.txt:13-24` does not list `esp_adc`. Whether IDF `driver` pulls in ADC in v5.x is UNVERIFIED.
- Netlist: `generate_kicad_sch.py:681` puts IS on U10 pin 5; `generate_kicad_sch.py:569` puts PROFET_IS on ESP pin 18 (IO10); R10 1.2 kΩ from PROFET_IS to GND (`generate_kicad_sch.py:694-695`). No clamp, divider, or RC filter.
- BTS7002-1EPP datasheet (UNVERIFIED web excerpt): RSENSE must be above 820 Ω (400 Ω with reverse-battery protection), typical 1.2 kΩ. IIS(FAULT) typ 5.5 mA, min 4.4 mA, max 10 mA. IIS(OLOFF) typ 2.5 mA. RC filter with at least 1 µs time constant recommended.

**Analysis:**
- Fault voltage V_IS = I_IS × R_SENSE. With typicals: 5.5 mA × 1.2 kΩ ≈ 6.6 V. Range 4.4 mA to 10 mA gives 5.3 V to 12 V. All exceed the ESP32-S3 pad maximum (about 3.6 V, UNVERIFIED).
- Even the datasheet minimum R (820 Ω) gives 3.6 V at 4.4 mA. There is no datasheet-legal R_SENSE that is safe on the ESP pin without clamping or a divider.
- Firmware keeps DEN high while ignition is on (`board_pins.c:68`), so a latched fault while running puts this voltage on GPIO10.

**Failure mode / trigger:** Overcurrent, overtemperature, or short to GND or VS while ignition is on. IS drives the ESP pad beyond its rating.

**Consequence:** Damage to ESP32-S3 GPIO10 and possibly neighbouring pins via ESD structures. This is the "burns boards" failure. The fault signal is also unusable because the ADC is never read.

**Fix sketch:**
1. Add a clamp (Zener to GND plus series R) or a divider that keeps V_IS under about 3.0 V at maximum fault current, after confirming kILIS and the fault table.
2. Add the RC filter (at least 1 µs) the datasheet recommends.
3. If the feature is kept, initialise `adc_oneshot` on ADC1 channel 9 and add `esp_adc` to REQUIRES if the pinned IDF needs it.

**Verification:** Datasheet check of kILIS, IIS(FAULT), and the clamp values for the chosen R; simulation of the network; bench fault test with a current-limited supply (not run here).

---

### F-05-08 - Deep sleep: PROFET IN and other outputs not held; sleep path never called [P1] [VERIFIED code; UNVERIFIED electrical]

**Evidence:**
- `firmware/main/power_manager.c:32-51`: sets timer and ext0 wakeup (`:39`, `:43`), then drives three GPIOs LOW before `esp_deep_sleep_start()`: SSR_KILL (`:46`), SSR_STARTER (`:47`), SIREN (`:48`).
- PROFET_IN (GPIO8) and PROFET_DEN (GPIO15) are not touched in the sleep path.
- No caller of `power_manager_enter_deep_sleep` in `firmware/` (grep: only definition and `power_manager.h:23` declaration).
- No `gpio_hold`, `gpio_deep_sleep_hold`, `rtc_gpio_*` calls in `firmware/`.
- `PROJECT.md:77-82` describes a sleep model that is not implemented.

**Analysis:**
- Setting a pin LOW right before sleep does not latch it. Per ESP-IDF docs (UNVERIFIED), `gpio_hold_en` does not hold a digital GPIO through deep sleep on ESP32-S3; use `gpio_deep_sleep_hold_en()` with the per-pin hold. RTC-capable pins can also use `rtc_gpio_isolate`.
- After deep sleep the digital pads revert. GPIO8 has no pull and no external pull-down in the netlist (`generate_kicad_sch.py:676-683`: IN on pin 2 with nothing else). BTS7002 datasheet (UNVERIFIED): IN should be tied to GND or via 4.7 kΩ when unused. A floating IN could let the channel conduct during sleep.
- GPIO38 is not an RTC pin (UNVERIFIED), so only digital hold applies.
- The output pulldowns (`board_pins.c:27`) add roughly 73 µA per high pin (UNVERIFIED). Not measured.

**Failure mode / trigger:** Entry to deep sleep through any future caller. PROFET_IN floats; the ignition channel may close.

**Consequence:** Battery drain above the 100 µA target in `PROJECT.md:77`. Unintended ignition during sleep is a theft concern if the path is enabled.

**Fix sketch:**
1. Before sleep: drive PROFET_IN and DEN LOW; `gpio_hold_en` on IN, DEN, SSR_KILL, SSR_STARTER, SIREN, PWRKEY (released = HIGH); `gpio_deep_sleep_hold_en()`.
2. Add an external 4.7-10 kΩ pull-down on PROFET_IN and DEN in the netlist.
3. Wire `power_manager_enter_deep_sleep` into a real sleep path, or delete the dead code and update `PROJECT.md`.

**Verification:** Sleep current measurement on the board (not run here); netlist check of the IN pull-down.

---

### F-05-09 - Wake mapping differs from PROJECT.md; EXT1 is labelled but never configured [P2] [VERIFIED]

**Evidence:**
- `PROJECT.md:81-82`: modem RI wakes EXT0, LIS3DH INT wakes EXT1.
- `firmware/main/power_manager.c:43`: `esp_sleep_enable_ext0_wakeup(PIN_IMU_INT1, 1)`. IMU is EXT0. `power_manager.c:23-25` labels EXT1 as "Modem Ring Indicator", but no `esp_sleep_enable_ext1_*` call exists.
- GPIO4 is RTC_GPIO4 and the ext0 range is 0-21 (Espressif docs, UNVERIFIED), so EXT0 on GPIO4 is legal.
- RI is on GPIO21 in the netlist (`generate_kicad_sch.py:574`), which is RTC_GPIO21 (UNVERIFIED).

**Analysis:** Code wakes on IMU only. The mapping disagrees with PROJECT.md. The IMU wake is useless until F-05-02 is fixed. Putting RI on GPIO21 collides with F-05-04, so RI needs a third pin.

**Fix sketch:** Pick the EXT0/EXT1 assignment and align PROJECT.md and code. Use `esp_sleep_enable_ext1_wakeup_io()` if two pins must wake. Give RI its own RTC pin separate from STATUS.

**Verification:** Netlist and firmware diff; wake test on the board (not run here).

---

### F-05-10 - Kill SSR pin GPIO3 floats from reset until `board_pins_init`; no pull network [P2] [INFERRED]

**Evidence:**
- Strapping (UNVERIFIED): GPIO3 has no internal pull at reset, input-enable on.
- `board_pins.h:22` `PIN_SSR_KILL GPIO3`, Active HIGH = ignition kill. `board_pins.c:37` drives LOW only after `gpio_config`.
- `generate_kicad_sch.py:278` ties GPIO3 to SSR_KILL_DRV; R12 330 Ω (`generate_kicad_sch.py:702`) to U12 LED. No pull-down anywhere on that net.
- `firmware/main/actuator_safety.c:92`: kill SSR ON = pulls ignition to chassis (engine kill).
- GPIO3 is a boot-mode strap only when EFUSE_STRAP_JTAG_SEL=1 (default off, UNVERIFIED), so boot mode is unaffected by default.

**Analysis:** A floating CMOS input does not source the roughly 2 mA the LED path would need, so in practice U12 stays off (INFERRED). The design still depends on that, and noise or a fault on the LED side is not excluded. A kill SSR that engages during boot is a safety item.

**Failure mode / trigger:** Hardware reset or brownout with the pin in an undefined state.

**Consequence:** Engine kill during boot (low probability, safety-of-life).

**Fix sketch:** Add 10 kΩ pull-downs on the SSR_KILL, SSR_STARTER, and SIREN_DRV nets so reset is explicitly OFF. Confirm U12's input current and threshold (UNVERIFIED).

**Verification:** ERC on the added pull-downs; datasheet threshold check (not run here).

---

### F-05-11 - Siren gate has no pull-down; siren may sound at reset or power-up [P2] [INFERRED]

**Evidence:**
- `generate_kicad_sch.py:714-715`: Q5 (DMN6075S) gate is SIREN_DRV from GPIO11 directly. No gate resistor or pull-down.
- `board_pins.h:29` `PIN_SIREN_CTRL GPIO_NUM_11`, Active HIGH. `board_pins.c:41` drives it LOW after init.

**Analysis:** Gate threshold (typically 1-2 V, UNVERIFIED) and a floating gate can conduct on noise. The gate floats until `board_pins_init`. A siren chirp at power-up is a nuisance and drains the battery.

**Fix sketch:** Add a 100 kΩ gate-to-source pull-down on Q5.

**Verification:** Netlist diff; reset bench test (not run here).

---

### F-05-12 - LIS3DH I2C: external pull-ups present (R19/R20 4.7 kΩ); spec and BOM refdes disagree; 400 kHz marginal on internal pull-ups alone [P2] [UNVERIFIED]

**Evidence:**
- Firmware: `firmware/main/sensors_imu.c:7-8` 400 kHz; `sensors_imu.c:18-20` enables internal pull-ups on SDA and SCL.
- Netlist: `generate_kicad_sch.py:739-741`: R19 4.7 kΩ SCL to +3V3, R20 4.7 kΩ SDA to +3V3. External pull-ups exist.
- Spec: `PCB_SPECIFICATION.md:114` says R1/R2 (4.7 kΩ) are the I2C pull-ups. Generator R1 is 54.9 kΩ buck FB (`generate_kicad_sch.py:526`), R2 is 10 kΩ buck FB (`generate_kicad_sch.py:528`). BOM `automoto_bom_jlcpcb.csv:31` lists R1 as 54.9 kΩ.
- Address: `firmware/main/sensors_imu.h:12` says SA0=GND gives 0x18. Netlist: `generate_kicad_sch.py:733` ties LIS3DH pin 7 (SA0) to GND, and pin 8 (CS) to +3V3 (I2C mode). Consistent with 0x18.

**Analysis:**
- Address 0x18 is consistent with the netlist (VERIFIED). The LIS3DH address table is UNVERIFIED.
- Fast mode (400 kHz) needs rise time at or under 300 ns (I2C spec, UNVERIFIED). With R = 4.7 kΩ, rise time ≈ 0.847·R·C, so the bus must stay under about 75 pF. Realistic board capacitance is UNVERIFIED.
- Internal pull-ups alone (about 45 kΩ, UNVERIFIED) would allow only about 8 pF and would fail at 400 kHz. The netlist does not rely on them alone, so this is a margin note, not a fault.
- The internal pull-ups add in parallel (about 4 kΩ). Harmless, not needed.

**Fix sketch:** Reconcile refdes across spec, BOM, and netlist. Keep the external pull-ups, measure bus capacitance on the layout, and drop to 100 kHz if rise time fails. Document or remove the internal pull-ups.

**Verification:** Rise-time measurement on the board (not run here); LIS3DH I2C timing from datasheet.

---

### F-05-13 - PROFET IN and DEN driven together; DEN high with IN low draws IIS(OLOFF); fault-latch clear timing undocumented [P2] [UNVERIFIED]

**Evidence:**
- `firmware/main/board_pins.c:65-70`: `board_set_ignition` drives IN and DEN together; comment `:68` "Teşhis hattını da aç" (also open the diagnostic line).
- BTS7002 datasheet (UNVERIFIED): DEN is the diagnostic enable (high = diagnosis on and IS active; low = IS high-impedance). It does not enable the channel; IN does. DEN falling edge clears the protection latch depending on IN state and DEN pulse length (datasheet ch. 8.3, not in repo).

**Analysis (Q6):** DEN is a diagnostic enable (UNVERIFIED), not a channel enable, and firmware's comment and naming are correct. If DEN were assumed to be a channel enable, the bike would never switch on, but nothing would be damaged. The real hazards are:
- (a) DEN high while IN is low (OFF_Diag) draws IIS(OLOFF) through R10 into GPIO10 (see F-05-07).
- (b) DEN falls with IN on power-off, so latch-clear behaviour depends on datasheet ch. 8.3 timing that firmware does not model.

**Failure mode / trigger:** Overtemperature or overcurrent latches the channel. Firmware cycles ignition, but whether the DEN/IN sequence clears the latch is UNVERIFIED.

**Consequence:** Channel may stay latched off after a fault. Reliability issue, not a direct safety path.

**Fix sketch:** Implement and document an explicit DEN pulse sequence after faults per datasheet ch. 8.3. Keep DEN low when ignition is off. Tie DEN to GND via 4.7 kΩ if the diagnostic is unused.

**Verification:** Datasheet ch. 8.3 timing; bench fault test (not run here).

---

### F-05-14 - Output pulldowns on all nine outputs; PWRKEY conflicts [P3] [INFERRED]

**Evidence:** `firmware/main/board_pins.c:12-21` lists nine output pins; `board_pins.c:27` enables pulldown on all of them.

**Analysis:**
- PWRKEY: the pulldown holds the key in the pressed state when idle, which conflicts with SIM808 active-LOW (F-05-05).
- LEDs: pulldown adds roughly 73 µA per pin when driven high (UNVERIFIED), negligible against roughly 3 mA LED current.
- BTS7002 IN: pulldown helps hold IN low after init. Does not help during reset (F-05-08).
- GPIO45/46: pulldown is applied after reset, so it does not change the strap value sampled at reset (F-05-06).

**Fix sketch:** Remove pulldown from PWRKEY. Keep it elsewhere; add external pull-downs where F-05-08 and F-05-10 call for them.

**Verification:** Firmware change plus ERC.

---

### F-05-15 - Battery-sense ADC pins in netlist but absent from firmware and spec [P2] [VERIFIED]

**Evidence:**
- Netlist: `generate_kicad_sch.py:572-573` puts ADC_VBAT_BIKE on IO13 and ADC_VBAT_INT on IO14. Dividers R15/R16 (100k/10k, `generate_kicad_sch.py:718-721`) and R17/R18 (100k/100k, `generate_kicad_sch.py:722-725`).
- Firmware: no define for GPIO13 or GPIO14.
- `PROJECT.md:113-117` telemetry expects `bike_voltage` and `internal_voltage`. No code reads them.
- `PCB_SPECIFICATION.md` does not mention these nets. The BOM lists R1 (54.9 kΩ) as "input voltage sense" (`automoto_bom_jlcpcb.csv:31`), which matches R15/R16 only loosely; R1 in the netlist is the buck feedback divider.

**Analysis:** GPIO13 and GPIO14 are ADC2 channels (UNVERIFIED). ADC2 cannot be used while Wi-Fi is active; BLE is not affected (UNVERIFIED). Dividers look reasonable: 12 V / 11 ≈ 1.1 V; 3.2-3.65 V LiFePO4 / 2 ≈ 1.6-1.8 V (INFERRED from resistor values). Readings are never taken.

**Fix sketch:** Add defines and ADC reads, or remove the dividers and document the removal. Fix the R1 BOM description.

**Verification:** Netlist check; firmware review.

---

### F-05-16 - Simulation and doc drift: Wokwi and sim README do not match the PCB; neutral button models firmware, not hardware [P3] [VERIFIED]

**Evidence:**
- `sim/wokwi/diagram.json:80-94` wires GPIO 47, 48, 46, 8, 9, 3, 11, 12, 4. All nine match `board_pins.h`. Not wired in Wokwi: GPIO5, 6, 7, 10, 15, 17, 18, 21, 38, and I2C 1/2.
- Wokwi GSM LED on GPIO46 (`diagram.json:84`); PCB puts it on GPIO45 (F-05-03).
- Wokwi neutral pushbutton (`diagram.json:91-92`) pulls GPIO12 LOW when pressed to GND, with no pull-up in the diagram. This models firmware's active-LOW, not the netlist's topology (F-05-01).
- `sim/README.md:74-82` lists the same GPIO set and GSM LED on GPIO46.
- `sim/renode/automoto.repl:27-30` labels UART0 "USB Serial JTAG / Debug Console (GPIO 19/20)" and UART1 GPIO 17/18. Consistent with firmware, not checked against an IDF build.

**Fix sketch:** When F-05-01, F-05-03, and F-05-04 land, update `diagram.json` and `sim/README.md` in the same change.

**Verification:** Diff of `diagram.json` against `board_pins.h` after the fixes.

---

### F-05-17 - Spec, BOM, and generator refdes drift for R1-R4, R13, R14, R18-R20 [P3] [VERIFIED]

| Refdes | PCB spec | BOM (csv) | Generator (py) |
|---|---|---|---|
| R1 | 4.7k I2C SDA pull-up (`PCB_SPECIFICATION.md:114`) | 54.9k input voltage sense (csv:31) | 54.9k buck FB top (`generate_kicad_sch.py:526`) |
| R2 | 4.7k I2C SCL pull-up (`:114`) | 10k group (csv:26) | 10k buck FB bottom (`:528`) |
| R3 | 10k EN pull-up (`:115`) | 2.4k ISET (csv:32) | 2.4k CHRG_ISET (`:537`) |
| R4 | 10k neutral pull-up (`:116`) | 10k group (csv:26) | 10k EN pull-up (`:596`) |
| R13 | 4.7k opto input (`:122`) | 4.7k group (csv:27) | 4.7k neutral anode (`:707`) |
| R14 | 100k Q1 gate bias (`:123`) | 10k group (csv:26) | 10k neutral pull-down (`:711`) |
| R18 | 10k NTC (`:126`) | 100k group (csv:28) | 100k INT bottom (`:724`) |
| R19 | 4.7k PWRKEY series (`:127`) | 4.7k PWRKEY/signal (csv:27) | 4.7k SCL pull-up (`:739`) |
| R20 | 10k SIM_DATA pull-up (`:128`) | 4.7k group (csv:27) | 4.7k SDA pull-up (`:741`) |

Also: SIM808 TXD/RXD pin numbers are 67/68 in the spec (`PCB_SPECIFICATION.md:184-185`) and 9/10 in the generator (`generate_kicad_sch.py:641-642`).

**Fix sketch:** Use the generator as the source of truth (it produces the ERC/DRC output). Regenerate spec and BOM tables from it.

**Verification:** Diff after regeneration.

---

### F-05-18 - Unused and undocumented pins [P3] [VERIFIED]

- `board_pins.h:37-38` defines `PIN_CAN_TX/RX` (GPIO6/7) with no driver. The CAN transceiver U8 is in the netlist (`generate_kicad_sch.py:744`) but not in firmware.
- `board_pins.h:34` `PIN_IMU_INT2` (GPIO5): no read or config path.
- `firmware/README.md:74-85` omits GPIO4, 5, 6, 7, 15, 19, 20, and 21 (STATUS shown only as a combined row).
- USB D-/D+ on GPIO19/20 (`generate_kicad_sch.py:276-277`) are used by the USB port. Firmware does not claim them, so no conflict today.
- `platformio.ini:16-17` says 8 MB octal PSRAM, but `sdkconfig.defaults` has no SPIRAM setting. GPIO33-37 are reserved by octal PSRAM on N16R8 modules (UNVERIFIED). Firmware and netlist do not use them.

**Fix sketch:** Document reserved and unused pins in the README pin table.

**Verification:** Documentation review.

---

## Analysis Question Answers

**Q1 - Three-way pin table:** Appendix A.

**Q2 - Strapping pins.**
- GPIO0: not driven by firmware. Boot button SW2 (`generate_kicad_sch.py:600-601`) goes to GND; internal weak pull-up only. Pressing SW2 at reset enters download mode (UNVERIFIED, boot table).
- GPIO3 (PIN_SSR_KILL): F-05-10. Default eFuse makes it irrelevant to boot mode.
- GPIO45 (LED on PCB): F-05-06. VDD_SPI risk.
- GPIO46 (PIN_LED_GSM in firmware): F-05-03, F-05-06. GPIO46=1 with GPIO0=0 is invalid. Also ROM message control.
- `GPIO_PULLDOWN_ENABLE` (`board_pins.c:27`): applied after reset, after the strap latches sampled (datasheet excerpt, UNVERIFIED). It does not change boot mode for the current boot. It restores the default for the next hardware reset.

**Q3 - GPIO legality.** Checked against Espressif's table (UNVERIFIED):
- Flash/PSRAM 26-32: not used. 33-37 (octal): not used. Netlist leaves IO35-37 NC (`generate_kicad_sch.py:584-587`).
- USB 19/20: not used by firmware; used by USB-C in the netlist (`generate_kicad_sch.py:276-277`).
- JTAG (GPIO39-42): not used.
- RTC-capable 0-21 for ext0/ext1: EXT0 uses GPIO4, in range.
- Input-only pins: none on ESP32-S3 (INFERRED; the Espressif table has no input-only class).
- No duplicate GPIO in `board_pins.h`.

**Q4 - GPIO4/5 read but not configured.** F-05-02. Read returns 0 (UNVERIFIED docs; no firmware config). GPIO4 is RTC_GPIO4 (UNVERIFIED), so ext0 is legal.

**Q5 - PROFET IS on ADC.** GPIO10 = ADC1_CH9 (UNVERIFIED, Espressif table). ADC driver not initialised anywhere. `esp_adc` not in REQUIRES. BTS7002 IS needs R_SENSE ≥820 Ω with RC filter; no clamp in netlist. F-05-07.

**Q6 - DEN.** Diagnostic enable (UNVERIFIED). Does not gate the channel. F-05-13.

**Q7 - Polarity audit.** Appendix B.

**Q8 - Pulldown conflicts.** F-05-14. PWRKEY is the important one. LED leakage negligible. BTS7002 IN threshold compatible with 3.3 V (datasheet excerpt, UNVERIFIED). Modem boot straps: the pulldown on GPIO46 does not affect the sampled value.

**Q9 - I2C.** F-05-12.

**Q10 - Deep sleep holds.** F-05-08 and Appendix C.

**Q11 - Wokwi cross-check.** F-05-16 and Appendix A (Wokwi column).

---

## Open Questions

1. **LTV-356T pinout and neutral switch wiring:** confirm pin 3 vs pin 4 and whether the switch closes to GND in neutral. This decides the F-05-01 direction. Confirm with BOM datasheet (C1709) and the physical harness.
2. **EFUSE_VDD_SPI_FORCE on the N16R8 module, and VDD_SPI requirement of the flash and PSRAM.** Confirm with the ESP32-S3-WROOM-1 N16R8 module datasheet.
3. **SIM808 STATUS pin number:** 52 or 66? Spec says 52; generator says 66 (NETLIGHT on 52). Confirm with SIM808 hardware design PDF.
4. **SIM808 PWRKEY series resistor:** netlist has none; BOM and spec say R19 4.7 kΩ. Intentional? Confirm by schematic review.
5. **BTS7002 IS voltage budget:** what does the designer intend at maximum fault current? Confirm with datasheet ch. 9 and kILIS for the module; bench fault test.
6. **Does IDF `driver` REQUIRES pull in `esp_adc` in the pinned IDF?** Moot until ADC is used. Confirm in `components/driver/CMakeLists.txt` of the pinned IDF.
7. **LIS3DH INT polarity and default config:** confirm from datasheet registers (CTRL_REG3, INT1_CFG).

---

## Suggested Jobs

1. **P0 - Neutral interlock polarity (F-05-01):** Fix the opto/R14 wiring to a fail-safe polarity; add a hardware-series neutral path; firmware rejects ambiguous input. Re-run ERC. Depends on the LTV-356T datasheet.
2. **P0 - IMU init and alarm path (F-05-02):** Implement LIS3DH init (WHO_AM_I, CTRL, INT1 routing); configure GPIO4 as input; add I2C poll fallback. Add a test that the motion path asserts.
3. **P1 - LED and strap re-map (F-05-03, F-05-06):** Pick a non-strapping GPIO for the GSM LED; disconnect NETLIGHT contention; pull-down on GPIO45 if it stays. Update firmware, Wokwi, README, and netlist together.
4. **P1 - Modem STATUS and PWRKEY (F-05-04, F-05-05):** Rewire STATUS; PWRKEY active-LOW with idle HIGH; add series R or transistor per SIMCom; fix `modem_is_alive()`.
5. **P1 - IS clamp and ADC (F-05-07):** Clamp or divider plus RC filter on IS; init ADC1 channel 9 if the feature is kept.
6. **P1 - Deep sleep holds (F-05-08):** External pull-downs on PROFET_IN and DEN; holds and `gpio_deep_sleep_hold_en`; wire or delete the sleep path.
7. **P2 - Reset-state pull-downs (F-05-10, F-05-11):** 10 kΩ on SSR_KILL, SSR_STARTER, SIREN_DRV; 100 kΩ gate pull-down on Q5.
8. **P2 - Wake mapping (F-05-09):** Decide EXT0/EXT1 assignment; align PROJECT.md.
9. **P2 - I2C margin (F-05-12):** Measure rise time on layout; 100 kHz if it fails; document internal pull-ups.
10. **P2 - DEN fault-clear procedure (F-05-13):** Implement the datasheet ch. 8.3 sequence.
11. **P3 - Doc and refdes reconciliation (F-05-14 to F-05-18):** Regenerate spec and BOM tables from the generator; README pin table; align Wokwi.

---

## Appendix A - Three-way pin table (Q1, Q11)

Hardware column: spec = `PCB_SPECIFICATION.md`, gen = `generate_kicad_sch.py`, Wokwi = `sim/wokwi/diagram.json`.

| Signal | board_pins.h | firmware/README.md | PROJECT.md | Hardware (spec / gen / BOM / Wokwi) | Conflict? |
|---|---|---|---|---|---|
| I2C SDA | GPIO1 (`h:18`) | GPIO1 (`README:76`) | no pin number | spec pin 39 IO1 (`:174`); gen `:590` | No (pull-up refdes drift, F-05-17) |
| I2C SCL | GPIO2 (`h:19`) | GPIO2 (`README:76`) | no pin | spec pin 38 (`:173`); gen `:589` | No |
| SSR_KILL | GPIO3 (`h:22`) | GPIO3 (`README:77`) | no pin | spec pin 15 (`:162`); gen `:278` | No pin conflict; floats pre-init (F-05-10) |
| PROFET_IN | GPIO8 (`h:23`) | GPIO8 (`README:78`) | no pin | spec pin 12 (`:159`); gen `:275`; Wokwi `diagram.json:86` | No |
| SSR_STARTER | GPIO9 (`h:24`) | GPIO9 (`README:79`) | no pin | spec pin 17 (`:164`); gen `:280` | No |
| PROFET_DEN | GPIO15 (`h:25`) | **absent** | no pin | spec pin 8 (`:156`); gen `:271` | **Yes**: README row missing |
| PROFET_IS | GPIO10 (`h:26`), comment ADC1_CH9 | GPIO10 ADC (`README:80`) | no pin | spec pin 18 (`:165`); gen `:569` | No pin conflict; ADC not implemented (F-05-07) |
| SIREN_CTRL | GPIO11 (`h:29`) | GPIO11 (`README:81`) | no pin | spec pin 19 (`:166`); gen `:570` | No |
| SENSE_NEUTRAL | GPIO12 (`h:30`) | GPIO12 (`README:82`) | interlock described (`:158`) | spec pin 20 (`:167`); gen `:571`; netlist polarity inverted | **Yes**: polarity (F-05-01) |
| IMU_INT1 | GPIO4 (`h:33`) | **absent** | EXT0/EXT1 mapping only (`:81-82`) | spec pin 4 (`:152`); gen `:267`, `:555`; Wokwi `diagram.json:93` | **Yes**: README absent; wake mapping (F-05-09) |
| IMU_INT2 | GPIO5 (`h:34`) | **absent** | none | spec pin 5 (`:153`); gen `:268` | **Yes**: README absent |
| CAN_TX / RX | GPIO6 / 7 (`h:37-38`) | **absent** | CAN ops (`:66`) | spec pins 6/7 (`:154-155`); gen `:269-270` | Not used by firmware (F-05-18) |
| MODEM_TX | GPIO17 (`h:41`) | GPIO17/18 (`README:83`) | none | spec pin 10 IO17 (`:157`); SIM808 pin 67 (`:184`); gen u1 pin 10 net GSM_RXD (`:561`); SIM808 pin 10 (`:642`) | Pin number and net-name drift (F-05-17); direction correct |
| MODEM_RX | GPIO18 (`h:42`) | GPIO17/18 (`README:83`) | none | spec pin 11 IO18 (`:158`); SIM808 pin 68 (`:185`); gen u1 pin 11 net GSM_TXD (`:562`); SIM808 pin 9 (`:641`) | Same as MODEM_TX |
| MODEM_STATUS | GPIO21 (`h:43`) | GPIO21 STATUS (`README:84`) | none | spec pin 23 IO21 MODEM_STATUS (`:168`); gen GPIO21 = GSM_RI (`:574`); STATUS on GPIO40 (`:584`) | **Yes**: wrong pin (F-05-04) |
| MODEM_PWRKEY | GPIO38 (`h:44`) | GPIO38 PWRKEY (`README:84`) | none | spec pin 31 (`:172`) + R19 4.7k (`:182`); gen `:582`, no series R; R19 is SCL (`:739`) | **Yes**: polarity (F-05-05); series R missing |
| LED_GSM | GPIO46 (`h:47`) | GPIO46..48 (`README:85`) | none | spec pin 16 IO46 (`:163`); **gen pin 16 = NC (`:566`), LED on pin 26 IO45 (`:577`)**; Wokwi GPIO46 (`diagram.json:84`) | **Yes** (F-05-03) |
| LED_ALARM | GPIO47 (`h:48`) | GPIO46..48 (`README:85`) | none | spec pin 24 (`:169`); gen `:575`; Wokwi `diagram.json:80` | No |
| LED_BLE | GPIO48 (`h:49`) | GPIO46..48 (`README:85`) | none | spec pin 25 (`:170`); gen `:576`; Wokwi `diagram.json:82` | No |
| BOOT (GPIO0) | not defined | absent | none | spec pin 27 (`:171`); gen `:578`; SW2 `:600-601` | Not in firmware (OK) |
| USB D-/D+ | not defined | absent | "yerel USB" (`:59`) | spec pins 13/14 (`:160-161`); gen `:276-277` | Not in firmware (OK) |
| ADC_VBAT_BIKE / INT | not defined | absent | telemetry fields (`:113-117`) | gen IO13/IO14 (`:572-573`), R15-R18 (`:718-725`); not in spec | **Yes**: firmware and spec omit (F-05-15) |
| GSM_DTR | not defined | absent | none | gen IO39 pin 32 (`:583`) | Schematic only |
| EN (CHIP_PU) | n/a | n/a | n/a | spec R3 10k (`:115`); gen R4 10k EN (`:596`); gen R3 is 2.4k (`:537`) | Refdes drift (F-05-17) |
| Wokwi relays / LEDs / buttons | n/a | n/a | n/a | `diagram.json:80-94`: 8, 9, 3, 11, 12, 4, 46, 47, 48 | Match `board_pins.h`; missing pins listed in F-05-16 |

## Appendix B - Polarity audit (Q7)

Reset/boot state: pins are not driven until `board_pins_init` (`board_pins.c:37-45`). Power-loss: VDD gone, pins float, loads see no drive.

| Define | Claimed | Code path | Netlist path | Reset / boot / power-loss | Safe level | Verdict |
|---|---|---|---|---|---|---|
| PIN_SSR_KILL GPIO3 | Active HIGH (`h:22`) | `board_set_kill_ssr` (`board_pins.c:88-90`): HIGH = kill | R12 330 Ω to U12 LED (`gen:702`) | Floating until init; no pull | LOW (no kill) | Polarity OK; floats pre-init (F-05-10) |
| PIN_PROFET_IN GPIO8 | Active HIGH (`h:23`) | `board_set_ignition` (`board_pins.c:67`) | U10 pin 2 direct, no R (`gen:678`) | Floating at reset; no external pull-down | LOW (off) | Polarity OK; pre-init and sleep risk (F-05-08) |
| PIN_SSR_STARTER GPIO9 | Active HIGH (`h:24`) | `board_set_starter` (`board_pins.c:80`), gated by neutral (`:75`) | R11 330 Ω to U11 LED (`gen:697-700`) | Floating at reset | LOW (no crank) | Polarity OK; gated by inverted neutral (F-05-01) |
| PIN_PROFET_DEN GPIO15 | Diagnostic enable (`h:25`) | Driven with IN (`board_pins.c:68`) | U10 pin 3 direct (`gen:679`) | Floating at reset | LOW (diagnosis off) | Datasheet-consistent (UNVERIFIED); latch clear (F-05-13) |
| PIN_SIREN_CTRL GPIO11 | Active HIGH (`h:29`) | `board_set_siren` (`board_pins.c:85`) | Q5 gate direct, no pull (`gen:714-715`) | Floating gate | LOW (siren off) | Polarity OK; gate float (F-05-11) |
| PIN_SENSE_NEUTRAL GPIO12 | Active LOW = neutral (`h:30`; `board_pins.c:96`) | `gpio_get_level == 0` means neutral | U9 pin 4 = +3V3, pin 3 = out, R14 10k to GND (`gen:709-712`) | Opto off gives LOW = reads NEUTRAL | HIGH (IN GEAR) | **Inverted, fail-open** (F-05-01, P0) |
| PIN_MODEM_PWRKEY GPIO38 | Pulse output (`h:44`); firmware drives HIGH to pulse | `modem_power_cycle` (`modem.c:51-53`); pulldown idle LOW (`board_pins.c:27`) | SIM808 pin 1, no series R (`gen:638`) | Module pull-up = released when floating; firmware drives LOW at init (`board_pins.c:42`) | HIGH (released) | **Inverted vs SIM808 active-LOW** (F-05-05, P1) |
| PIN_LED_GSM GPIO46 | Active HIGH (`h:47`) | `main.c:52-54` | NC on PCB (`gen:566`) | Strap GPIO46 (pulled down) | LOW | Not connected; LED on GPIO45 (F-05-03) |
| PIN_LED_ALARM GPIO47 | Active HIGH (`h:48`) | `main.c:31-33`, `board_pins.c:44` | R5 to LED1 anode, cathode GND (`gen:603-605`) | Floating: LED off | LOW | OK |
| PIN_LED_BLE GPIO48 | Active HIGH (`h:49`) | `ble_keyless.c:23` | R6 to LED2 (`gen:608-611`) | Floating: LED off | LOW | OK |
| PIN_MODEM_STATUS GPIO21 | HIGH = alive (`modem.c:60`) | `modem_is_alive` | netlist GPIO21 = RI (`gen:574`) | RI idle HIGH (UNVERIFIED): always alive | n/a | **Wrong signal** (F-05-04, P1) |
| PIN_IMU_INT1 GPIO4 | Active HIGH motion (`sensors_imu.c:40`) | `gpio_get_level == 1` | LIS3DH INT1 push-pull, LOW default (UNVERIFIED) | Unconfigured: reads 0 | n/a | **Never configured** (F-05-02, P0) |
| PIN_IMU_INT2 GPIO5 | none | none | LIS3DH INT2 (`gen:268`) | Unconfigured | n/a | Unused (F-05-18) |
| PIN_I2C_SDA/SCL GPIO1/2 | I2C | `sensors_imu.c:15-22` | R19/R20 4.7k to +3V3 (`gen:739-741`) | Pull-ups present | n/a | OK (F-05-12) |
| PIN_MODEM_TX/RX GPIO17/18 | UART1 | `modem.c:35` | net labels swapped vs pin (F-05-17) | UART | n/a | Direction OK |
| PIN_CAN_TX/RX GPIO6/7 | defined only | none | U8 CAN (`gen:744`) | n/a | n/a | Unused (F-05-18) |

## Appendix C - Deep-sleep hold matrix (Q10)

RTC membership per Espressif GPIO table (UNVERIFIED). Hold state is the current firmware state: `grep` finds no hold or isolate call anywhere in `firmware/`, and the sleep path has no caller, so every row is "No".

| GPIO | Function | Firmware before sleep | Required in sleep | RTC-capable | Held today | Needed |
|---|---|---|---|---|---|---|
| 8 | PROFET_IN | not set | LOW | yes (RTC_GPIO8) | No | `gpio_hold_en` + `gpio_deep_sleep_hold_en`; `rtc_gpio_isolate`; external pull-down (F-05-08) |
| 15 | PROFET_DEN | not set | LOW | yes (RTC_GPIO15) | No | Same |
| 3 | SSR_KILL | LOW (`power_manager.c:46`) | LOW | yes (RTC_GPIO3) | No (state lost in deep sleep) | Hold + isolate |
| 9 | SSR_STARTER | LOW (`power_manager.c:47`) | LOW | yes (RTC_GPIO9) | No | Hold + isolate |
| 11 | SIREN_CTRL | LOW (`power_manager.c:48`) | LOW | yes (RTC_GPIO11) | No | Hold + isolate |
| 38 | PWRKEY | not set | HIGH (released) | no (UNVERIFIED) | No | Digital hold only |
| 46 | LED_GSM | not set | LOW | no (UNVERIFIED) | No | Digital hold only (or move the LED, F-05-03) |
| 47, 48 | LEDs | not set | LOW | no (UNVERIFIED) | No | Digital hold |
| 4 | IMU_INT1 | input (ext0 only) | input | yes (RTC_GPIO4) | Ext0 config only | Keep as input with pull per LIS3DH INT polarity |
| 10 | PROFET_IS | not used | high-Z | yes (RTC_GPIO10) | n/a | Clamp (F-05-07) |

## Appendix D - Clean checks (no finding)

- No firmware use of GPIO26-37 (flash/PSRAM/octal), GPIO19/20 (USB), or GPIO39-42 (JTAG). Checked by reading `board_pins.h` and all `firmware/main/*.c`.
- No duplicate GPIO assignment in `board_pins.h`.
- All LED outputs are active-HIGH with the LED anode on the GPIO side (`generate_kicad_sch.py:603-611`). Firmware polarity matches the netlist for alarm (47) and BLE (48).
- LIS3DH address 0x18 is consistent with SA0 to GND (`generate_kicad_sch.py:733`) and `sensors_imu.h:12`.
- Input-only pins: none on ESP32-S3 (INFERRED from the Espressif table, which has no input-only class).
- `board_pins_init` sets all nine outputs to their LOW reset levels (`board_pins.c:37-45`), which matches the default-safe design (`PROJECT.md:160`), except PWRKEY (F-05-05).

## Sources (external; all UNVERIFIED until a pinned datasheet is in repo)

- ESP32-S3 GPIO and RTC GPIO table, restrictions, and deep-sleep hold notes: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/gpio.html (fetched this session).
- ESP32-S3 sleep modes and wakeup sources: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/sleep_modes.html (fetched this session).
- ESP32-S3 datasheet strapping and power pins (web excerpts; Espressif datasheet v1.6 and later).
- BTS7002-1EPP datasheet (web excerpts; Infineon PROFET+2 12V v1.03).
- SIM808 hardware design v1.02/v1.03 (web excerpts; SIMCom).
- LIS3DH datasheet (web excerpts; STMicroelectronics DocID 17530).
