#!/usr/bin/env python3
"""
AutoMoto — Akıllı Motosiklet Güvenlik, Keyless Go & Telemetri Sistemi
KiCad 10 Otomatik Şematik Üreteci (automoto.kicad_sch) — v4.0 (SIMCom SIM808 GSM/GPRS/GPS Mimarisi)

Üretilen Şematik Blokları:
1. 12V Otomotiv Giriş Koruması (PTC Sigorta F1, 1500W TVS D1, Ters Polarite P-FET Q1)
2. Güç Yönetimi (TPS54302 3.86V 3A Senkron Buck U4, CN3058 LiFePO4 Şarj U5, LM66100 İdeal Diyot U6, AP2112K 3.3V LDO U7)
3. Ana İşlemci (ESP32-S3-WROOM-1U U1), USB Type-C (J4 + USBLC6 ESD D3), Butonlar (SW1/SW2) ve Durum LED'leri (LED1..3)
4. Hücresel & GPS Modülü (SIMCom SIM808 LCC-68 U2), Nano SIM Yuvası (J2), GSM & GPS U.FL Anten Konnektörleri (ANT1, ANT2)
5. Katı-Hal (Solid-State) Güç ve Emniyet Anahtarlama (BTS7002-1EPP 25A PROFET U10, VO14642AAB Marş/Kill-Switch SSR U11/U12, LTV-356T Boş Vites Opto U9, DMN6075S Siren MOSFET Q5)
6. Sensör & Haberleşme (LIS3DH 3-Eksen MEMS IMU U3, SN65HVD230 CAN Alıcı-Verici U8 + PESD2CAN ESD D2, Molex 14-Pin Ana Tesisat Soketi J1)
"""

import os
import uuid

PROJECT_ROOT = "/home/sorcnr/Documents/automoto"
PCB_DIR = os.path.join(PROJECT_ROOT, "hardware/pcb")
OUTPUT_SCH = os.path.join(PCB_DIR, "automoto.kicad_sch")


def det_uuid(seed_str):
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"automoto-sch-v4-{seed_str}"))


def build_lib_symbol(sym_id, ref_prefix, val_name, footprint_name, left_pins, right_pins, box_w=20.32):
    """
    Sol ve sağ pin listelerinden standart KiCad 10 (version 20250114) sembol tanımı oluşturur.
    Pin formatı: (pin_number, pin_name, elec_type)
    elec_type: input, output, bidirectional, passive, power_in, power_out, open_collector
    """
    max_rows = max(len(left_pins), len(right_pins), 1)
    half_h = max((max_rows + 1) * 1.27, 5.08)
    # 2.54mm ızgaraya hizala
    half_h = round(half_h / 2.54) * 2.54
    if half_h < max_rows * 1.27:
        half_h += 2.54

    half_w = round((box_w / 2.0) / 2.54) * 2.54
    pin_len = 2.54

    lines = []
    lines.append(f'\t\t(symbol "automoto:{sym_id}"')
    lines.append('\t\t\t(pin_names (offset 1.016))')
    lines.append('\t\t\t(exclude_from_sim no)')
    lines.append('\t\t\t(in_bom yes)')
    lines.append('\t\t\t(on_board yes)')
    lines.append(f'\t\t\t(property "Reference" "{ref_prefix}" (at {-half_w:.2f} {half_h + 1.905:.3f} 0) (effects (font (size 1.27 1.27)) (justify left)))')
    lines.append(f'\t\t\t(property "Value" "{val_name}" (at {-half_w:.2f} {-half_h - 1.905:.3f} 0) (effects (font (size 1.27 1.27)) (justify left)))')
    lines.append(f'\t\t\t(property "Footprint" "{footprint_name}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append('\t\t\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append(f'\t\t\t(property "Description" "{val_name}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')

    # Gövde dikdörtgeni
    lines.append(f'\t\t\t(symbol "{sym_id}_0_1"')
    lines.append(f'\t\t\t\t(rectangle (start {-half_w:.2f} {half_h:.2f}) (end {half_w:.2f} {-half_h:.2f})')
    lines.append('\t\t\t\t\t(stroke (width 0.254) (type default))')
    lines.append('\t\t\t\t\t(fill (type background))')
    lines.append('\t\t\t\t)')
    lines.append('\t\t\t)')

    # Pinler
    lines.append(f'\t\t\t(symbol "{sym_id}_1_1"')
    top_y = half_h - 2.54
    for idx, (pnum, pname, ptype) in enumerate(left_pins):
        py = top_y - idx * 2.54
        px = -half_w - pin_len
        lines.append(f'\t\t\t\t(pin {ptype} line (at {px:.2f} {py:.2f} 0) (length {pin_len:.2f})')
        lines.append(f'\t\t\t\t\t(name "{pname}" (effects (font (size 1.016 1.016))))')
        lines.append(f'\t\t\t\t\t(number "{pnum}" (effects (font (size 1.016 1.016))))')
        lines.append('\t\t\t\t)')

    for idx, (pnum, pname, ptype) in enumerate(right_pins):
        py = top_y - idx * 2.54
        px = half_w + pin_len
        lines.append(f'\t\t\t\t(pin {ptype} line (at {px:.2f} {py:.2f} 180) (length {pin_len:.2f})')
        lines.append(f'\t\t\t\t\t(name "{pname}" (effects (font (size 1.016 1.016))))')
        lines.append(f'\t\t\t\t\t(number "{pnum}" (effects (font (size 1.016 1.016))))')
        lines.append('\t\t\t\t)')

    lines.append('\t\t\t)')
    lines.append('\t\t)')

    geom = {
        "half_w": half_w,
        "half_h": half_h,
        "pin_len": pin_len,
        "top_y": top_y,
        "left_pins": left_pins,
        "right_pins": right_pins,
    }
    return "\n".join(lines), geom


def generate_schematic():
    root_uuid = det_uuid("root-sheet")
    lib_defs = []
    lib_geoms = {}
    instances = []
    wires = []
    labels = []
    no_connects = []
    texts = []

    def register_symbol(sym_id, ref_prefix, val_name, fp_name, left_pins, right_pins, box_w=20.32):
        s_txt, geom = build_lib_symbol(sym_id, ref_prefix, val_name, fp_name, left_pins, right_pins, box_w)
        lib_defs.append(s_txt)
        lib_geoms[sym_id] = (ref_prefix, val_name, fp_name, geom)

    def place_component(sym_id, ref, val, fp_name, sx, sy, pin_nets):
        """
        Bileşeni (sx, sy) koordinatına yerleştirir ve tüm bacaklarına tel + net etiketi (veya no_connect) bağlar.
        sx ve sy 2.54mm ızgaranın tam katı olmalıdır.
        """
        sx = round(sx / 2.54) * 2.54
        sy = round(sy / 2.54) * 2.54
        _, _, default_fp, geom = lib_geoms[sym_id]
        use_fp = fp_name if fp_name else default_fp
        half_w = geom["half_w"]
        half_h = geom["half_h"]
        pin_len = geom["pin_len"]
        top_y = geom["top_y"]

        comp_uuid = det_uuid(f"comp-{ref}")
        inst = []
        inst.append('\t(symbol')
        inst.append(f'\t\t(lib_id "automoto:{sym_id}")')
        inst.append(f'\t\t(at {sx:.2f} {sy:.2f} 0)')
        inst.append('\t\t(unit 1)')
        inst.append('\t\t(exclude_from_sim no)')
        inst.append('\t\t(in_bom yes)')
        inst.append('\t\t(on_board yes)')
        inst.append('\t\t(dnp no)')
        inst.append(f'\t\t(uuid "{comp_uuid}")')
        inst.append(f'\t\t(property "Reference" "{ref}" (at {sx - half_w:.2f} {sy - half_h - 2.0:.2f} 0) (effects (font (size 1.27 1.27)) (justify left)))')
        inst.append(f'\t\t(property "Value" "{val}" (at {sx - half_w:.2f} {sy + half_h + 2.0:.2f} 0) (effects (font (size 1.1 1.1)) (justify left)))')
        inst.append(f'\t\t(property "Footprint" "{use_fp}" (at {sx:.2f} {sy:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        inst.append(f'\t\t(property "Datasheet" "" (at {sx:.2f} {sy:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        inst.append(f'\t\t(property "Description" "{val}" (at {sx:.2f} {sy:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))')

        all_pins = list(geom["left_pins"]) + list(geom["right_pins"])
        for pnum, _, _ in all_pins:
            inst.append(f'\t\t(pin "{pnum}" (uuid "{det_uuid(f"pin-{ref}-{pnum}")}"))')

        inst.append('\t\t(instances')
        inst.append('\t\t\t(project "automoto"')
        inst.append(f'\t\t\t\t(path "/{root_uuid}" (reference "{ref}") (unit 1))')
        inst.append('\t\t\t)')
        inst.append('\t\t)')
        inst.append('\t)')
        instances.append("\n".join(inst))

        stub_len = 5.08
        # Sol pin bağlantıları
        for idx, (pnum, pname, _) in enumerate(geom["left_pins"]):
            py_rel = top_y - idx * 2.54
            px_rel = -half_w - pin_len
            wx1 = sx + px_rel
            wy1 = sy - py_rel
            net_name = pin_nets.get(str(pnum), "NC")
            if net_name in ("NC", None, ""):
                no_connects.append(f'\t(no_connect (at {wx1:.2f} {wy1:.2f}) (uuid "{det_uuid(f"nc-{ref}-{pnum}")}"))')
            else:
                wx2 = wx1 - stub_len
                wires.append(
                    f'\t(wire (pts (xy {wx2:.2f} {wy1:.2f}) (xy {wx1:.2f} {wy1:.2f})) '
                    f'(stroke (width 0) (type default)) (uuid "{det_uuid(f"w-{ref}-{pnum}")}"))'
                )
                labels.append(
                    f'\t(label "{net_name}" (at {wx2:.2f} {wy1:.2f} 180) '
                    f'(effects (font (size 1.016 1.016)) (justify right bottom)) '
                    f'(uuid "{det_uuid(f"lbl-{ref}-{pnum}")}"))'
                )

        # Sağ pin bağlantıları
        for idx, (pnum, pname, _) in enumerate(geom["right_pins"]):
            py_rel = top_y - idx * 2.54
            px_rel = half_w + pin_len
            wx1 = sx + px_rel
            wy1 = sy - py_rel
            net_name = pin_nets.get(str(pnum), "NC")
            if net_name in ("NC", None, ""):
                no_connects.append(f'\t(no_connect (at {wx1:.2f} {wy1:.2f}) (uuid "{det_uuid(f"nc-{ref}-{pnum}")}"))')
            else:
                wx2 = wx1 + stub_len
                wires.append(
                    f'\t(wire (pts (xy {wx1:.2f} {wy1:.2f}) (xy {wx2:.2f} {wy1:.2f})) '
                    f'(stroke (width 0) (type default)) (uuid "{det_uuid(f"w-{ref}-{pnum}")}"))'
                )
                labels.append(
                    f'\t(label "{net_name}" (at {wx2:.2f} {wy1:.2f} 0) '
                    f'(effects (font (size 1.016 1.016)) (justify left bottom)) '
                    f'(uuid "{det_uuid(f"lbl-{ref}-{pnum}")}"))'
                )

    def add_section_header(title, x_mm, y_mm):
        texts.append(
            f'\t(text "{title}" (exclude_from_sim no) (at {x_mm:.2f} {y_mm:.2f} 0) '
            f'(effects (font (size 2.54 2.54) bold) (justify left bottom)) '
            f'(uuid "{det_uuid(f"hdr-{title}")}"))'
        )

    # =========================================================================
    # 1. SEMBOL KÜTÜPHANESİ TANIMLARI (TÜM AKTİF VE PASİF BİLEŞENLER)
    # =========================================================================

    # Pasif 2-Pin Semboller
    register_symbol("R_SMD", "R", "R_0603", "Resistor_SMD:R_0603_1608Metric",
                    [("1", "1", "passive")], [("2", "2", "passive")], box_w=7.62)
    register_symbol("C_SMD", "C", "C_0603", "Capacitor_SMD:C_0603_1608Metric",
                    [("1", "1", "passive")], [("2", "2", "passive")], box_w=7.62)
    register_symbol("L_SMD", "L", "IHLP2020_6.8uH", "Inductor_SMD:L_Vishay_IHLP-2020",
                    [("1", "1", "passive")], [("2", "2", "passive")], box_w=10.16)
    register_symbol("FUSE_PTC", "F", "1812L200PR_2A", "Fuse:Fuse_1812_4532Metric",
                    [("1", "IN", "passive")], [("2", "OUT", "passive")], box_w=10.16)
    register_symbol("TVS_SMC", "D", "TPSMC36A_1500W", "Diode_SMD:D_SMC",
                    [("1", "K", "passive")], [("2", "A", "passive")], box_w=10.16)
    register_symbol("LED_0603", "LED", "LED_0603", "LED_SMD:LED_0603_1608Metric",
                    [("1", "K", "passive")], [("2", "A", "passive")], box_w=7.62)
    register_symbol("M25_HOLE", "H", "M2.5_Mount", "MountingHole:MountingHole_2.7mm_M2.5_Pad_Via",
                    [("1", "CHASSIS_GND", "passive")], [], box_w=7.62)

    # Buton (KXT331 / KMR2 4-Pad)
    register_symbol("SW_KMR2", "SW", "KXT331LFS", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2",
                    [("1", "SW_A", "passive")], [("2", "SW_B_GND", "passive")], box_w=10.16)

    # Q1: SQJ411EP PowerPAK SO-8 P-MOSFET
    register_symbol("SQJ411EP", "Q", "SQJ411EP_P-FET", "Package_SO:PowerPAK_SO-8_Single",
                    [("1", "S1", "power_out"), ("2", "S2", "passive"), ("3", "S3", "passive"), ("4", "G", "input")],
                    [("5", "D_TAB", "passive")], box_w=15.24)

    # Q5: DMN6075S SOT-23 N-MOSFET
    register_symbol("DMN6075S", "Q", "DMN6075S_Siren", "Package_TO_SOT_SMD:SOT-23",
                    [("1", "G", "input"), ("2", "S", "passive")],
                    [("3", "D", "passive")], box_w=12.70)

    # U4: TPS54302DDCR SOT-23-6 Buck
    register_symbol("TPS54302", "U", "TPS54302DDCR", "Package_TO_SOT_SMD:SOT-23-6",
                    [("2", "VIN", "power_in"), ("5", "EN", "input"), ("4", "GND", "power_in")],
                    [("1", "SW", "power_out"), ("6", "BOOT", "passive"), ("3", "FB", "input")], box_w=17.78)

    # U5: CN3058 SOIC-8 LiFePO4 Charger
    register_symbol("CN3058", "U", "CN3058_LiFePO4", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                    [("4", "VIN", "power_in"), ("1", "TEMP", "input"), ("2", "ISET", "passive"), ("3", "GND", "power_in")],
                    [("5", "BAT", "power_out"), ("8", "FB", "input"), ("7", "~CHRG", "open_collector"), ("6", "~DONE", "open_collector")], box_w=17.78)

    # U6: LM66100DCKR SOT-23-6 Ideal Diode
    register_symbol("LM66100", "U", "LM66100DCKR", "Package_TO_SOT_SMD:SOT-23-6",
                    [("1", "VIN", "power_in"), ("3", "~CE", "input"), ("2", "GND", "power_in")],
                    [("6", "VOUT", "power_out"), ("4", "ST", "output"), ("5", "NC", "passive")], box_w=17.78)

    # U7: AP2112K-3.3TRG1 SOT-23-5 LDO
    register_symbol("AP2112K", "U", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5",
                    [("1", "VIN", "power_in"), ("3", "EN", "input"), ("2", "GND", "power_in")],
                    [("5", "VOUT", "power_out"), ("4", "NC", "passive")], box_w=17.78)

    # J3: JST-PH 2-Pin LiFePO4 Battery
    register_symbol("JST_PH_2P", "J", "JST-PH_LiFePO4", "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",
                    [("1", "VBAT+", "passive"), ("2", "GND", "passive")], [], box_w=12.70)

    # U1: ESP32-S3-WROOM-1U (41 Pads)
    u1_left = [
        ("1", "GND", "power_in"),
        ("2", "3V3", "power_in"),
        ("3", "EN", "input"),
        ("4", "IO4_IMU_INT1", "bidirectional"),
        ("5", "IO5_IMU_INT2", "bidirectional"),
        ("6", "IO6_CAN_TX", "bidirectional"),
        ("7", "IO7_CAN_RX", "bidirectional"),
        ("8", "IO15_PROFET_DEN", "bidirectional"),
        ("9", "IO16", "bidirectional"),
        ("10", "IO17_GSM_TXD", "bidirectional"),
        ("11", "IO18_GSM_RXD", "bidirectional"),
        ("12", "IO8_PROFET_IN", "bidirectional"),
        ("13", "IO19_USB_D-", "bidirectional"),
        ("14", "IO20_USB_D+", "bidirectional"),
        ("15", "IO3_KILL_SSR", "bidirectional"),
        ("16", "IO46", "bidirectional"),
        ("17", "IO9_STARTER_SSR", "bidirectional"),
        ("18", "IO10_PROFET_IS", "bidirectional"),
        ("19", "IO11_SIREN_PWM", "bidirectional"),
        ("20", "IO12_NEUTRAL_IN", "bidirectional"),
    ]
    u1_right = [
        ("21", "IO13_VBAT_BIKE", "bidirectional"),
        ("22", "IO14_VBAT_LIFEPO", "bidirectional"),
        ("23", "IO21_GSM_RI", "bidirectional"),
        ("24", "IO47_LED_ALARM", "bidirectional"),
        ("25", "IO48_LED_BLE", "bidirectional"),
        ("26", "IO45_LED_GSM", "bidirectional"),
        ("27", "IO0_BOOT", "bidirectional"),
        ("28", "IO35", "bidirectional"),
        ("29", "IO36", "bidirectional"),
        ("30", "IO37", "bidirectional"),
        ("31", "IO38_GSM_PWRKEY", "bidirectional"),
        ("32", "IO39_GSM_DTR", "bidirectional"),
        ("33", "IO40_GSM_STATUS", "bidirectional"),
        ("34", "IO41", "bidirectional"),
        ("35", "IO42", "bidirectional"),
        ("36", "RXD0", "bidirectional"),
        ("37", "TXD0", "bidirectional"),
        ("38", "IO2_I2C_SCL", "bidirectional"),
        ("39", "IO1_I2C_SDA", "bidirectional"),
        ("40", "GND_40", "power_in"),
        ("41", "GND_EP", "power_in"),
    ]
    register_symbol("ESP32_S3_WROOM_1U", "U", "ESP32-S3-WROOM-1U", "RF_Module:ESP32-S3-WROOM-1U", u1_left, u1_right, box_w=27.94)

    # U2: SIMCom SIM808 (GSM/GPRS + GPS, 68-Pin LCC 24x24mm)
    u2_left = [
        ("1", "PWRKEY", "input"),
        ("2", "NC_2", "passive"),
        ("3", "DTR", "input"),
        ("4", "RI", "output"),
        ("5", "DCD", "output"),
        ("6", "NC_6", "passive"),
        ("7", "CTS", "output"),
        ("8", "RTS", "input"),
        ("9", "TXD", "output"),
        ("10", "RXD", "input"),
        ("11", "DISP_CLK", "output"),
        ("12", "DISP_DATA", "bidirectional"),
        ("13", "DISP_DC", "output"),
        ("14", "DISP_CS", "output"),
        ("15", "VDD_EXT", "passive"),
        ("16", "~RESET", "input"),
        ("17", "GND_17", "power_in"),
        ("18", "GND_18", "power_in"),
        ("19", "MIC_P", "input"),
        ("20", "MIC_N", "input"),
        ("21", "SPK_P", "output"),
        ("22", "SPK_N", "output"),
        ("23", "KPLED", "input"),
        ("24", "USB_VBUS", "power_in"),
        ("25", "ADC", "input"),
        ("26", "VRTC", "power_in"),
        ("27", "DBG_TXD", "output"),
        ("28", "DBG_RXD", "input"),
        ("29", "GND_29", "power_in"),
        ("30", "SIM_VDD", "power_out"),
        ("31", "SIM_DATA", "bidirectional"),
        ("32", "SIM_CLK", "output"),
        ("33", "SIM_RST", "output"),
        ("34", "SIM_PRE", "input"),
    ]
    u2_right = [
        ("35", "PWM1", "output"),
        ("36", "PWM2", "output"),
        ("37", "SDA", "bidirectional"),
        ("38", "SCL", "output"),
        ("39", "GND_39", "power_in"),
        ("40", "BT_ANT", "passive"),
        ("41", "GND_41", "power_in"),
        ("42", "GPS_RF_IN", "passive"),
        ("43", "GND_43", "power_in"),
        ("44", "NC_44", "passive"),
        ("45", "GND_45", "power_in"),
        ("46", "GND_46", "power_in"),
        ("47", "NC_47", "passive"),
        ("48", "NC_48", "passive"),
        ("49", "NC_49", "passive"),
        ("50", "NC_50", "passive"),
        ("51", "NC_51", "passive"),
        ("52", "NETLIGHT", "output"),
        ("53", "GND_53", "power_in"),
        ("54", "GND_54", "power_in"),
        ("55", "VBAT_55", "power_in"),
        ("56", "VBAT_56", "power_in"),
        ("57", "VBAT_57", "power_in"),
        ("58", "GND_58", "power_in"),
        ("59", "GND_59", "power_in"),
        ("60", "GSM_ANT", "passive"),
        ("61", "GND_61", "power_in"),
        ("62", "GND_62", "power_in"),
        ("63", "GND_63", "power_in"),
        ("64", "GND_64", "power_in"),
        ("65", "GND_65", "power_in"),
        ("66", "STATUS", "output"),
        ("67", "GPIO11", "bidirectional"),
        ("68", "GPIO12", "bidirectional"),
    ]
    register_symbol("SIMCOM_SIM808", "U", "SIMCom_SIM808_GSM_GPS", "RF_GSM:SIMCom_SIM900", u2_left, u2_right, box_w=27.94)

    # J2: Nano SIM Yuvası
    register_symbol("NANO_SIM", "J", "Nano_SIM_Socket", "Connector_Card:nanoSIM_Hinged_CUI_NSIM-2-C",
                    [("1", "VCC", "power_in"), ("2", "RST", "input"), ("3", "CLK", "input"), ("7", "I/O", "bidirectional")],
                    [("5", "GND", "power_in"), ("6", "VPP", "passive"), ("CD", "CARD_DET", "passive"), ("SH", "SHIELD", "power_in")], box_w=17.78)

    # ANT1 / ANT2: U.FL Coaxial
    register_symbol("UFL_ANT", "ANT", "U.FL_Hirose", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
                    [("1", "RF_SIG", "passive")], [("2", "GND", "power_in")], box_w=12.70)

    # U3: LIS3DH LGA-16 MEMS IMU
    u3_left = [
        ("1", "VDD_IO", "power_in"),
        ("14", "VDD", "power_in"),
        ("4", "SCL", "input"),
        ("6", "SDA", "bidirectional"),
        ("7", "SDO_SA0", "input"),
        ("8", "CS", "input"),
        ("5", "GND_5", "power_in"),
        ("12", "GND_12", "power_in"),
    ]
    u3_right = [
        ("11", "INT1", "output"),
        ("9", "INT2", "output"),
        ("10", "RES_GND", "power_in"),
        ("2", "NC_2", "passive"),
        ("3", "NC_3", "passive"),
        ("13", "ADC3", "input"),
        ("15", "ADC2", "input"),
        ("16", "ADC1", "input"),
    ]
    register_symbol("LIS3DH", "U", "LIS3DH_IMU", "Package_LGA:LGA-16_3x3mm_P0.5mm", u3_left, u3_right, box_w=17.78)

    # U8: SN65HVD230DR CAN Transceiver
    register_symbol("SN65HVD230", "U", "SN65HVD230DR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                    [("3", "VCC", "power_in"), ("1", "D_TXD", "input"), ("4", "R_RXD", "output"), ("8", "RS_SLOPE", "input")],
                    [("7", "CANH", "bidirectional"), ("6", "CANL", "bidirectional"), ("5", "VREF", "output"), ("2", "GND", "power_in")], box_w=17.78)

    # D2: PESD2CAN SOT-23
    register_symbol("PESD2CAN", "D", "PESD2CAN", "Package_TO_SOT_SMD:SOT-23",
                    [("1", "CANH", "passive"), ("2", "CANL", "passive")],
                    [("3", "GND", "power_in")], box_w=12.70)

    # D3: USBLC6-2SC6 SOT-23-6
    register_symbol("USBLC6", "D", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
                    [("1", "I/O1_DN", "passive"), ("3", "I/O2_DP", "passive"), ("2", "GND", "power_in")],
                    [("6", "I/O1_CON", "passive"), ("4", "I/O2_CON", "passive"), ("5", "VBUS", "power_in")], box_w=17.78)

    # J4: USB Type-C 16-Pin
    j4_left = [
        ("A4", "VBUS_A4", "power_out"),
        ("A9", "VBUS_A9", "passive"),
        ("B4", "VBUS_B4", "passive"),
        ("B9", "VBUS_B9", "passive"),
        ("A5", "CC1", "bidirectional"),
        ("B5", "CC2", "bidirectional"),
        ("A8", "SBU1", "bidirectional"),
        ("B8", "SBU2", "bidirectional"),
    ]
    j4_right = [
        ("A6", "DP1", "bidirectional"),
        ("B6", "DP2", "bidirectional"),
        ("A7", "DN1", "bidirectional"),
        ("B7", "DN2", "bidirectional"),
        ("A1", "GND_A1", "power_in"),
        ("A12", "GND_A12", "power_in"),
        ("B1", "GND_B1", "power_in"),
        ("B12", "GND_B12", "power_in"),
        ("SH", "SHIELD", "power_in"),
    ]
    register_symbol("USB_C_16P", "J", "USB_C_GCT_USB4110", "Connector_USB:USB_C_Receptacle_GCT_USB4110", j4_left, j4_right, box_w=17.78)

    # U10: BTS7002-1EPP PROFET
    u10_left = [
        ("1", "GND", "power_in"),
        ("2", "IN", "input"),
        ("3", "DEN", "input"),
        ("4", "NC_4", "passive"),
        ("5", "IS", "output"),
        ("6", "NC_6", "passive"),
        ("7", "NC_7", "passive"),
        ("15", "VS_TAB", "power_in"),
    ]
    u10_right = [
        ("8", "OUT_8", "power_out"),
        ("9", "OUT_9", "passive"),
        ("10", "OUT_10", "passive"),
        ("11", "OUT_11", "passive"),
        ("12", "OUT_12", "passive"),
        ("13", "OUT_13", "passive"),
        ("14", "OUT_14", "passive"),
    ]
    register_symbol("BTS7002_1EPP", "U", "BTS7002-1EPP", "Package_SO:Infineon_PG-TSDSO-14-22", u10_left, u10_right, box_w=20.32)

    # U11 / U12 / U9: SOP-4 Opto / SSR
    register_symbol("SOP4_ISO", "U", "VO14642AAB_SSR", "Package_SO:SO-4_4.4x4.3mm_P2.54mm",
                    [("1", "LED_A", "passive"), ("2", "LED_K", "passive")],
                    [("4", "SW_1", "passive"), ("3", "SW_2", "passive")], box_w=15.24)

    # J1: Molex Micro-Fit 14P
    j1_left = [
        ("1", "BIKE_12V_IN", "passive"),
        ("2", "BIKE_GND", "power_out"),
        ("3", "IGNITION_IN", "power_out"),
        ("4", "IGNITION_OUT", "passive"),
        ("5", "STARTER_CTRL", "passive"),
        ("6", "KILL_SW_A", "passive"),
        ("7", "KILL_SW_B", "passive"),
    ]
    j1_right = [
        ("8", "NEUTRAL_SENSE", "passive"),
        ("9", "SIREN_POS", "passive"),
        ("10", "SIREN_NEG", "passive"),
        ("11", "CAN_HIGH", "bidirectional"),
        ("12", "CAN_LOW", "bidirectional"),
        ("13", "EXT_ALERT_LED", "passive"),
        ("14", "SPARE_GND", "power_in"),
    ]
    register_symbol("MOLEX_14P", "J", "Molex_MicroFit_14P", "Connector_Molex:Molex_Micro-Fit_3.0_43045-1400_2x07_P3.00mm_Horizontal", j1_left, j1_right, box_w=30.48)

    # =========================================================================
    # 2. ŞEMATİK SAYFA YERLEŞİMİ (A2: 594 x 420 mm, 6 Mühendislik Bloğu)
    # =========================================================================

    # --- BLOK 1: 12V GİRİŞ KORUMASI & GÜÇ YÖNETİMİ (Sol Üst) ---
    add_section_header("1. 12V OTOMOTIV KORUMA, 3.86V BUCK (TPS54302), LiFePO4 SARJ (CN3058) & 3.3V LDO", 25.4, 22.86)

    place_component("FUSE_PTC", "F1", "1812L200PR_2A", "Fuse:Fuse_1812_4532Metric", 45.72, 40.64,
                    {"1": "+12V_RAW", "2": "+12V_PROT"})
    place_component("TVS_SMC", "D1", "TPSMC36A_1500W", "Diode_SMD:D_SMC", 91.44, 40.64,
                    {"1": "+12V_PROT", "2": "GND"})
    place_component("SQJ411EP", "Q1", "SQJ411EP_P-FET", "Package_SO:PowerPAK_SO-8_Single", 142.24, 43.18,
                    {"1": "+12V_IN", "2": "+12V_IN", "3": "+12V_IN", "4": "GND", "5": "+12V_PROT"})

    place_component("C_SMD", "C2", "22uF_50V_X7R", "Capacitor_SMD:C_1210_3225Metric", 45.72, 68.58,
                    {"1": "+12V_IN", "2": "GND"})
    place_component("TPS54302", "U4", "TPS54302DDCR_Buck", "Package_TO_SOT_SMD:SOT-23-6", 96.52, 73.66,
                    {"2": "+12V_IN", "5": "+12V_IN", "4": "GND", "1": "BUCK_SW", "6": "BUCK_BOOT", "3": "BUCK_FB"})
    place_component("C_SMD", "C5", "100nF_BOOT", "Capacitor_SMD:C_0603_1608Metric", 149.86, 66.04,
                    {"1": "BUCK_SW", "2": "BUCK_BOOT"})
    place_component("L_SMD", "L1", "IHLP2020_6.8uH", "Inductor_SMD:L_Vishay_IHLP-2020", 149.86, 86.36,
                    {"1": "BUCK_SW", "2": "VSYS_3V86"})
    place_component("R_SMD", "R1", "54.9k_FB_TOP", "Resistor_SMD:R_0603_1608Metric", 45.72, 88.90,
                    {"1": "VSYS_3V86", "2": "BUCK_FB"})
    place_component("R_SMD", "R2", "10k_FB_BOT", "Resistor_SMD:R_0603_1608Metric", 45.72, 109.22,
                    {"1": "BUCK_FB", "2": "GND"})
    place_component("C_SMD", "C1", "22uF_25V_X7R", "Capacitor_SMD:C_1210_3225Metric", 96.52, 106.68,
                    {"1": "VSYS_3V86", "2": "GND"})
    place_component("C_SMD", "C3", "47uF_10V_X7R", "Capacitor_SMD:C_1210_3225Metric", 149.86, 106.68,
                    {"1": "VSYS_3V86", "2": "GND"})

    place_component("CN3058", "U5", "CN3058_Charger", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 50.80, 139.70,
                    {"4": "VSYS_3V86", "1": "GND", "2": "CHRG_ISET", "3": "GND", "5": "VBAT_LIFEPO4", "8": "VBAT_LIFEPO4", "7": "NC", "6": "NC"})
    place_component("R_SMD", "R3", "2.4k_ISET", "Resistor_SMD:R_0603_1608Metric", 104.14, 129.54,
                    {"1": "CHRG_ISET", "2": "GND"})
    place_component("JST_PH_2P", "J3", "JST-PH_LiFePO4", "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal", 104.14, 149.86,
                    {"1": "VBAT_LIFEPO4", "2": "GND"})
    place_component("LM66100", "U6", "LM66100DCKR_IdealDiode", "Package_TO_SOT_SMD:SOT-23-6", 152.40, 139.70,
                    {"1": "VBAT_LIFEPO4", "3": "VSYS_3V86", "2": "GND", "6": "VSYS_3V86", "4": "NC", "5": "NC"})
    place_component("AP2112K", "U7", "AP2112K-3.3_LDO", "Package_TO_SOT_SMD:SOT-23-5", 152.40, 172.72,
                    {"1": "VSYS_3V86", "3": "VSYS_3V86", "2": "GND", "5": "+3V3", "4": "NC"})
    place_component("C_SMD", "C6", "10uF_3V3_DEC", "Capacitor_SMD:C_0603_1608Metric", 104.14, 172.72,
                    {"1": "+3V3", "2": "GND"})

    # --- BLOK 2: ANA MİKRODENETLEYİCİ ESP32-S3, USB-C, BUTONLAR & LED'LER (Orta Üst) ---
    add_section_header("2. ANA ISLEMCI (ESP32-S3-WROOM-1U), YEREL USB-C, RESET/BOOT & DURUM LED'LERI", 210.82, 22.86)

    u1_nets = {
        "1": "GND",
        "2": "+3V3",
        "3": "ESP_EN",
        "4": "IMU_INT1",
        "5": "IMU_INT2",
        "6": "CAN_TX",
        "7": "CAN_RX",
        "8": "PROFET_DEN",
        "9": "NC",
        "10": "GSM_RXD",
        "11": "GSM_TXD",
        "12": "PROFET_IN",
        "13": "USB_DN",
        "14": "USB_DP",
        "15": "SSR_KILL_DRV",
        "16": "NC",
        "17": "SSR_STARTER_DRV",
        "18": "PROFET_IS",
        "19": "SIREN_DRV",
        "20": "NEUTRAL_OUT",
        "21": "ADC_VBAT_BIKE",
        "22": "ADC_VBAT_INT",
        "23": "GSM_RI",
        "24": "LED_ALARM_DRV",
        "25": "LED_BLE_DRV",
        "26": "LED_GSM_DRV",
        "27": "ESP_BOOT",
        "28": "NC",
        "29": "NC",
        "30": "NC",
        "31": "GSM_PWRKEY",
        "32": "GSM_DTR",
        "33": "GSM_STATUS",
        "34": "NC",
        "35": "NC",
        "36": "NC",
        "37": "NC",
        "38": "I2C_SCL",
        "39": "I2C_SDA",
        "40": "GND",
        "41": "GND",
    }
    place_component("ESP32_S3_WROOM_1U", "U1", "ESP32-S3-WROOM-1U-N16R8", "RF_Module:ESP32-S3-WROOM-1U", 254.00, 78.74, u1_nets)

    place_component("R_SMD", "R4", "10k_EN_PU", "Resistor_SMD:R_0603_1608Metric", 220.98, 142.24,
                    {"1": "+3V3", "2": "ESP_EN"})
    place_component("SW_KMR2", "SW1", "KXT331LFS_RESET", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", 220.98, 162.56,
                    {"1": "ESP_EN", "2": "GND"})
    place_component("SW_KMR2", "SW2", "KXT331LFS_BOOT", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", 220.98, 182.88,
                    {"1": "ESP_BOOT", "2": "GND"})

    place_component("R_SMD", "R5", "330R_ALARM", "Resistor_SMD:R_0603_1608Metric", 279.40, 142.24,
                    {"1": "LED_ALARM_DRV", "2": "LED1_A"})
    place_component("LED_0603", "LED1", "RED_ALARM", "LED_SMD:LED_0603_1608Metric", 322.58, 142.24,
                    {"1": "GND", "2": "LED1_A"})

    place_component("R_SMD", "R6", "330R_BLE", "Resistor_SMD:R_0603_1608Metric", 279.40, 162.56,
                    {"1": "LED_BLE_DRV", "2": "LED2_A"})
    place_component("LED_0603", "LED2", "BLUE_BLE", "LED_SMD:LED_0603_1608Metric", 322.58, 162.56,
                    {"1": "GND", "2": "LED2_A"})

    place_component("R_SMD", "R7", "330R_GSM", "Resistor_SMD:R_0603_1608Metric", 279.40, 182.88,
                    {"1": "LED_GSM_DRV", "2": "LED3_A"})
    place_component("LED_0603", "LED3", "GREEN_GSM", "LED_SMD:LED_0603_1608Metric", 322.58, 182.88,
                    {"1": "GND", "2": "LED3_A"})

    # USB-C & USBLC6 ESD
    j4_nets = {
        "A4": "VBUS_5V", "A9": "VBUS_5V", "B4": "VBUS_5V", "B9": "VBUS_5V",
        "A5": "USB_CC1", "B5": "USB_CC2", "A8": "NC", "B8": "NC",
        "A6": "USB_CON_DP", "B6": "USB_CON_DP",
        "A7": "USB_CON_DN", "B7": "USB_CON_DN",
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
    }
    place_component("USB_C_16P", "J4", "Type-C_16P", "Connector_USB:USB_C_Receptacle_GCT_USB4110", 342.90, 55.88, j4_nets)
    place_component("USBLC6", "D3", "USBLC6-2SC6_ESD", "Package_TO_SOT_SMD:SOT-23-6", 342.90, 96.52,
                    {"1": "USB_DN", "3": "USB_DP", "2": "GND", "6": "USB_CON_DN", "4": "USB_CON_DP", "5": "VBUS_5V"})
    place_component("R_SMD", "R8", "5.1k_CC1", "Resistor_SMD:R_0603_1608Metric", 365.76, 119.38,
                    {"1": "USB_CC1", "2": "GND"})
    place_component("R_SMD", "R9", "5.1k_CC2", "Resistor_SMD:R_0603_1608Metric", 365.76, 139.70,
                    {"1": "USB_CC2", "2": "GND"})

    # --- BLOK 3: SIMCOM SIM808 GSM/GPRS + GPS MODÜLÜ, NANO SIM & ANTENLER (Sağ Üst) ---
    add_section_header("3. SIMCOM SIM808 (GSM/GPRS + GPS LCC-68), NANO SIM YUVASI (J2) & RF ANTENLER", 396.24, 22.86)

    u2_nets = {
        "1": "GSM_PWRKEY",
        "3": "GSM_DTR",
        "4": "GSM_RI",
        "9": "GSM_TXD",
        "10": "GSM_RXD",
        "15": "NC",
        "17": "GND", "18": "GND", "29": "GND", "39": "GND", "41": "GND", "43": "GND",
        "45": "GND", "46": "GND", "53": "GND", "54": "GND", "58": "GND", "59": "GND",
        "61": "GND", "62": "GND", "63": "GND", "64": "GND", "65": "GND",
        "26": "VSYS_3V86",
        "30": "SIM_VDD",
        "31": "SIM_DATA",
        "32": "SIM_CLK",
        "33": "SIM_RST",
        "42": "RF_GPS",
        "52": "LED_GSM_DRV",
        "55": "VSYS_3V86",
        "56": "VSYS_3V86",
        "57": "VSYS_3V86",
        "60": "RF_GSM",
        "66": "GSM_STATUS",
    }
    place_component("SIMCOM_SIM808", "U2", "SIMCom_SIM808_GSM_GPS", "RF_GSM:SIMCom_SIM900", 444.50, 99.06, u2_nets)

    place_component("C_SMD", "C4", "100uF_6.3V_Tantal", "Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D", 533.40, 43.18,
                    {"1": "VSYS_3V86", "2": "GND"})
    place_component("C_SMD", "C7", "100nF_SIM_DEC", "Capacitor_SMD:C_0603_1608Metric", 533.40, 63.50,
                    {"1": "SIM_VDD", "2": "GND"})
    place_component("NANO_SIM", "J2", "Nano_SIM_PushPull", "Connector_Card:nanoSIM_Hinged_CUI_NSIM-2-C", 533.40, 93.98,
                    {"1": "SIM_VDD", "2": "SIM_RST", "3": "SIM_CLK", "7": "SIM_DATA", "5": "GND", "6": "NC", "CD": "NC", "SH": "GND"})
    place_component("UFL_ANT", "ANT1", "GSM_IPEX_UFL", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical", 533.40, 127.00,
                    {"1": "RF_GSM", "2": "GND"})
    place_component("UFL_ANT", "ANT2", "GPS_IPEX_UFL", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical", 533.40, 149.86,
                    {"1": "RF_GPS", "2": "GND"})

    # --- BLOK 4: KATI-HAL (SOLID-STATE) ANAHTARLAMA MATRİSİ (Sol Alt) ---
    add_section_header("4. KATI-HAL ANAHTARLAMA: 25A PROFET (BTS7002), MARS/KILL SSR & SIREN SURUCU", 25.4, 205.74)

    u10_nets = {
        "1": "GND",
        "2": "PROFET_IN",
        "3": "PROFET_DEN",
        "4": "NC",
        "5": "PROFET_IS",
        "6": "NC",
        "7": "NC",
        "15": "IGNITION_IN",
        "8": "IGNITION_OUT",
        "9": "IGNITION_OUT",
        "10": "IGNITION_OUT",
        "11": "IGNITION_OUT",
        "12": "IGNITION_OUT",
        "13": "IGNITION_OUT",
        "14": "IGNITION_OUT",
    }
    place_component("BTS7002_1EPP", "U10", "BTS7002-1EPP_PROFET_30A", "Package_SO:Infineon_PG-TSDSO-14-22", 60.96, 241.30, u10_nets)
    place_component("R_SMD", "R10", "1.2k_IS_SENSE", "Resistor_SMD:R_0603_1608Metric", 124.46, 226.06,
                    {"1": "PROFET_IS", "2": "GND"})

    place_component("R_SMD", "R11", "330R_STARTER", "Resistor_SMD:R_0603_1608Metric", 48.26, 284.48,
                    {"1": "SSR_STARTER_DRV", "2": "SSR1_A"})
    place_component("SOP4_ISO", "U11", "VO14642AAB_Starter_SSR", "Package_SO:SO-4_4.4x4.3mm_P2.54mm", 104.14, 284.48,
                    {"1": "SSR1_A", "2": "GND", "4": "STARTER_CTRL", "3": "+12V_IN"})

    place_component("R_SMD", "R12", "330R_KILL", "Resistor_SMD:R_0603_1608Metric", 48.26, 309.88,
                    {"1": "SSR_KILL_DRV", "2": "SSR2_A"})
    place_component("SOP4_ISO", "U12", "VO14642AAB_KillSwitch_SSR", "Package_SO:SO-4_4.4x4.3mm_P2.54mm", 104.14, 309.88,
                    {"1": "SSR2_A", "2": "GND", "4": "KILL_SWITCH_A", "3": "KILL_SWITCH_B"})

    place_component("R_SMD", "R13", "4.7k_NEUTRAL", "Resistor_SMD:R_0603_1608Metric", 48.26, 335.28,
                    {"1": "+12V_IN", "2": "NEUTRAL_ANODE"})
    place_component("SOP4_ISO", "U9", "LTV-356T_Opto", "Package_SO:SO-4_4.4x4.3mm_P2.54mm", 104.14, 335.28,
                    {"1": "NEUTRAL_ANODE", "2": "NEUTRAL_SENSE", "4": "+3V3", "3": "NEUTRAL_OUT"})
    place_component("R_SMD", "R14", "10k_NEUT_PD", "Resistor_SMD:R_0603_1608Metric", 154.94, 335.28,
                    {"1": "NEUTRAL_OUT", "2": "GND"})

    place_component("DMN6075S", "Q5", "DMN6075S_Siren", "Package_TO_SOT_SMD:SOT-23", 104.14, 360.68,
                    {"1": "SIREN_DRV", "2": "GND", "3": "SIREN_NEG"})

    # Gerilim Bölücüler (Akü & LiFePO4 ADC)
    place_component("R_SMD", "R15", "100k_BIKE_TOP", "Resistor_SMD:R_0603_1608Metric", 154.94, 274.32,
                    {"1": "+12V_IN", "2": "ADC_VBAT_BIKE"})
    place_component("R_SMD", "R16", "10k_BIKE_BOT", "Resistor_SMD:R_0603_1608Metric", 154.94, 294.64,
                    {"1": "ADC_VBAT_BIKE", "2": "GND"})
    place_component("R_SMD", "R17", "100k_INT_TOP", "Resistor_SMD:R_0603_1608Metric", 154.94, 314.96,
                    {"1": "VBAT_LIFEPO4", "2": "ADC_VBAT_INT"})
    place_component("R_SMD", "R18", "100k_INT_BOT", "Resistor_SMD:R_0603_1608Metric", 154.94, 360.68,
                    {"1": "ADC_VBAT_INT", "2": "GND"})

    # --- BLOK 5: LIS3DH IMU & CAN-BUS ALICI-VERİCİ (Orta Alt) ---
    add_section_header("5. HAREKET SENSORU (LIS3DH MEMS IMU) & OTOMOTIV CAN-BUS (SN65HVD230)", 210.82, 205.74)

    u3_nets = {
        "1": "+3V3", "14": "+3V3",
        "4": "I2C_SCL", "6": "I2C_SDA",
        "7": "GND", "8": "+3V3",
        "5": "GND", "12": "GND", "10": "GND",
        "11": "IMU_INT1", "9": "IMU_INT2",
        "2": "NC", "3": "NC", "13": "NC", "15": "NC", "16": "NC",
    }
    place_component("LIS3DH", "U3", "LIS3DH_IMU", "Package_LGA:LGA-16_3x3mm_P0.5mm", 254.00, 241.30, u3_nets)
    place_component("R_SMD", "R19", "4.7k_SCL_PU", "Resistor_SMD:R_0603_1608Metric", 322.58, 228.60,
                    {"1": "+3V3", "2": "I2C_SCL"})
    place_component("R_SMD", "R20", "4.7k_SDA_PU", "Resistor_SMD:R_0603_1608Metric", 322.58, 248.92,
                    {"1": "+3V3", "2": "I2C_SDA"})

    place_component("SN65HVD230", "U8", "SN65HVD230DR_CAN", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 254.00, 294.64,
                    {"3": "+3V3", "1": "CAN_TX", "4": "CAN_RX", "8": "GND", "7": "CAN_H", "6": "CAN_L", "5": "NC", "2": "GND"})
    place_component("PESD2CAN", "D2", "PESD2CAN", "Package_TO_SOT_SMD:SOT-23", 325.12, 294.64,
                    {"1": "CAN_H", "2": "CAN_L", "3": "GND"})
    place_component("C_SMD", "C8", "100nF_CAN_DEC", "Capacitor_SMD:C_0603_1608Metric", 254.00, 330.20,
                    {"1": "+3V3", "2": "GND"})

    # --- BLOK 6: MOLEX 14-PİN ANA TESİSAT SOKETİ & ŞASE DELİKLERİ (Sağ Alt) ---
    add_section_header("6. MOLEX MICRO-FIT 14-PIN ANA ARAC TESISAT SOKETI (J1) & SASE MONTAJ", 396.24, 205.74)

    j1_nets = {
        "1": "+12V_RAW",
        "2": "GND",
        "3": "IGNITION_IN",
        "4": "IGNITION_OUT",
        "5": "STARTER_CTRL",
        "6": "KILL_SWITCH_A",
        "7": "KILL_SWITCH_B",
        "8": "NEUTRAL_SENSE",
        "9": "+12V_IN",
        "10": "SIREN_NEG",
        "11": "CAN_H",
        "12": "CAN_L",
        "13": "LED1_A",
        "14": "GND",
    }
    place_component("MOLEX_14P", "J1", "Molex_14P_43045-1400", "Connector_Molex:Molex_Micro-Fit_3.0_43045-1400_2x07_P3.00mm_Horizontal", 457.20, 246.38, j1_nets)

    for idx, href in enumerate(["H1", "H2", "H3", "H4"]):
        place_component("M25_HOLE", href, "M2.5_Mounting_Hole", "MountingHole:MountingHole_2.7mm_M2.5_Pad_Via",
                        436.88 + idx * 30.48, 304.80, {"1": "GND"})

    # =========================================================================
    # 3. PROJE SEMBOL KÜTÜPHANESİNİ (automoto.kicad_sym & sym-lib-table) KAYDET
    # =========================================================================
    sym_lib_path = os.path.join(PCB_DIR, "automoto.kicad_sym")
    sym_lib_lines = [
        '(kicad_symbol_lib',
        '\t(version 20231120)',
        '\t(generator "kicad_symbol_editor")',
        '\t(generator_version "10.0")',
    ]
    for sdef in lib_defs:
        sym_lib_lines.append(sdef.replace('(symbol "automoto:', '(symbol "', 1))
    sym_lib_lines.append(')')
    with open(sym_lib_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sym_lib_lines) + "\n")

    sym_table_path = os.path.join(PCB_DIR, "sym-lib-table")
    with open(sym_table_path, "w", encoding="utf-8") as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "automoto")(type "KiCad")(uri "${KIPRJMOD}/automoto.kicad_sym")(options "")(descr "AutoMoto v4.0 Custom Symbol Library"))\n)\n')

    # =========================================================================
    # 4. KICAD 10 ŞEMATİK DOSYASINI BİRLEŞTİR VE KAYDET
    # =========================================================================
    sch_lines = []
    sch_lines.append('(kicad_sch')
    sch_lines.append('\t(version 20250114)')
    sch_lines.append('\t(generator "eeschema")')
    sch_lines.append('\t(generator_version "10.0")')
    sch_lines.append(f'\t(uuid "{root_uuid}")')
    sch_lines.append('\t(paper "A2")')
    sch_lines.append('\t(title_block')
    sch_lines.append('\t\t(title "AutoMoto Smart Motorcycle Telemetry, Keyless Go & Solid-State Security Unit")')
    sch_lines.append('\t\t(date "2026-10-25")')
    sch_lines.append('\t\t(rev "v4.0")')
    sch_lines.append('\t\t(company "AutoMoto Hardware Engineering")')
    sch_lines.append('\t\t(comment 1 "MCU: ESP32-S3-WROOM-1U | GSM/GPS: SIMCom SIM808 LCC-68 | IMU: LIS3DH")')
    sch_lines.append('\t\t(comment 2 "Solid-State Switching: Infineon BTS7002-1EPP 25A PROFET + 2x Vishay VO14642AAB SSR")')
    sch_lines.append('\t\t(comment 3 "Power Path: TPS54302 3.86V 3A Buck + CN3058 LiFePO4 Charger + LM66100 + AP2112K 3.3V")')
    sch_lines.append('\t)')
    sch_lines.append('\t(lib_symbols')
    sch_lines.extend(lib_defs)
    sch_lines.append('\t)')
    sch_lines.extend(texts)
    sch_lines.extend(instances)
    sch_lines.extend(wires)
    sch_lines.extend(labels)
    sch_lines.extend(no_connects)
    sch_lines.append('\t(sheet_instances')
    sch_lines.append('\t\t(path "/"')
    sch_lines.append('\t\t\t(page "1")')
    sch_lines.append('\t\t)')
    sch_lines.append('\t)')
    sch_lines.append('\t(embedded_fonts no)')
    sch_lines.append(')')

    with open(OUTPUT_SCH, "w", encoding="utf-8") as f:
        f.write("\n".join(sch_lines) + "\n")

    print(f"[BAŞARILI] KiCad 10 Şematik dosyası üretildi: {OUTPUT_SCH}")


if __name__ == "__main__":
    generate_schematic()

