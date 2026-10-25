#!/usr/bin/env python3
"""
AutoMoto — Akıllı Motosiklet Güvenlik ve Telemetri Sistemi
KiCad 10 İmalat ve Teklif Dosyaları Üreteci (Gerber, BOM, CPL, ZIP)
JLCPCB, ERKAR Elektronik ve Demsay Elektronik Standartlarına %100 Uyumlu
"""

import os
import sys
import shutil
import subprocess
import zipfile
import pandas as pd

PROJECT_ROOT = "/home/sorcnr/Documents/automoto"
PCB_FILE = os.path.join(PROJECT_ROOT, "hardware/pcb/automoto.kicad_pcb")
PROD_DIR = os.path.join(PROJECT_ROOT, "hardware/production")
GERBER_TMP = os.path.join(PROD_DIR, "gerber_files")

os.makedirs(PROD_DIR, exist_ok=True)
os.makedirs(GERBER_TMP, exist_ok=True)

# 1. Gerber & Drill Export via Flatpak KiCad CLI
print("[1/5] Gerber ve Drill dosyaları dışa aktarılıyor...")
shutil.rmtree(GERBER_TMP, ignore_errors=True)
os.makedirs(GERBER_TMP, exist_ok=True)

gerber_cmd = [
    "flatpak", "run", "--command=kicad-cli", "org.kicad.KiCad",
    "pcb", "export", "gerbers",
    "-o", GERBER_TMP,
    "--layers", "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
    "--no-x2",
    PCB_FILE
]
subprocess.run(gerber_cmd, check=True)

drill_cmd = [
    "flatpak", "run", "--command=kicad-cli", "org.kicad.KiCad",
    "pcb", "export", "drill",
    "-o", f"{GERBER_TMP}/",
    "--excellon-separate-th",
    "--excellon-units", "mm",
    PCB_FILE
]
subprocess.run(drill_cmd, check=True)

# Gerber ZIP
gerber_zip_path = os.path.join(PROD_DIR, "automoto_gerber_v4.0.zip")
with zipfile.ZipFile(gerber_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(GERBER_TMP):
        for file in files:
            file_path = os.path.join(root, file)
            zipf.write(file_path, arcname=file)
print(f" -> Gerber Paketi Oluşturuldu: {gerber_zip_path}")

# 2. CPL (Component Placement List / Centroid / Pick and Place)
print("[2/5] CPL (Pick and Place) koordinat dosyası üretiliyor...")
raw_pos_csv = os.path.join(PROD_DIR, "raw_pos.csv")
pos_cmd = [
    "flatpak", "run", "--command=kicad-cli", "org.kicad.KiCad",
    "pcb", "export", "pos",
    "--format", "csv",
    "--units", "mm",
    "-o", raw_pos_csv,
    PCB_FILE
]
subprocess.run(pos_cmd, check=True)

df_pos = pd.read_csv(raw_pos_csv)
# KiCad csv columns: Ref,Val,Package,PosX,PosY,Rot,Side
# Standard JLCPCB CPL columns: Designator, Val, Package, Mid X, Mid Y, Rotation, Layer
df_pos = df_pos.rename(columns={
    "Ref": "Designator",
    "Val": "Val",
    "Package": "Package",
    "PosX": "Mid X",
    "PosY": "Mid Y",
    "Rot": "Rotation",
    "Side": "Layer"
})
# Normalize Layer: top -> Top, bottom -> Bottom
df_pos["Layer"] = df_pos["Layer"].apply(lambda s: "Top" if str(s).lower() == "top" else "Bottom")

# Exclude mounting holes from CPL
df_pos_smt = df_pos[~df_pos["Designator"].str.startswith("H")].copy()

cpl_csv_path = os.path.join(PROD_DIR, "automoto_cpl_jlcpcb.csv")
df_pos_smt.to_csv(cpl_csv_path, index=False)
print(f" -> CPL Dosyası Oluşturuldu: {cpl_csv_path}")

if os.path.exists(raw_pos_csv):
    os.remove(raw_pos_csv)

# 3. BOM (Bill of Materials) Oluşturma
print("[3/5] BOM (Malzeme Listesi) JLCPCB/LCSC uyumlu olarak üretiliyor...")

BOM_DATABASE = [
    {
        "Comment": "ESP32-S3-WROOM-1U-N16R8",
        "Designator": "U1",
        "Footprint": "SMD Modül (18.0x19.2 mm)",
        "LCSC Part #": "C2913204",
        "Manufacturer": "Espressif Systems",
        "Package": "SMD Module",
        "Description": "Dual-Core 240MHz MCU, 16MB Flash, 8MB PSRAM, BLE 5.0, U.FL",
        "DNP": "NO"
    },
    {
        "Comment": "SIM808",
        "Designator": "U2",
        "Footprint": "LCC-68 (24.0x24.0 mm)",
        "LCSC Part #": "C126275",
        "Manufacturer": "SIMCom Wireless",
        "Package": "LCC-68",
        "Description": "Quad-Band GSM/GPRS + GPS/GNSS Modülü",
        "DNP": "NO"
    },
    {
        "Comment": "LIS3DHTR",
        "Designator": "U3",
        "Footprint": "LGA-16 (3.0x3.0 mm)",
        "LCSC Part #": "C71933",
        "Manufacturer": "STMicroelectronics",
        "Package": "LGA-16",
        "Description": "3-Eksen Ultra Düşük Güç Tüketimli MEMS İvmeölçer",
        "DNP": "NO"
    },
    {
        "Comment": "TPS54302DDCR",
        "Designator": "U4",
        "Footprint": "SOT-23-6",
        "LCSC Part #": "C93121",
        "Manufacturer": "Texas Instruments",
        "Package": "SOT-23-6",
        "Description": "4.5V-28V Giriş, 3.86V 3A Senkron Step-Down Buck Regülatör",
        "DNP": "NO"
    },
    {
        "Comment": "CN3058E",
        "Designator": "U5",
        "Footprint": "SOIC-8-EP",
        "LCSC Part #": "C112011",
        "Manufacturer": "Consonance Elec",
        "Package": "SOIC-8-EP",
        "Description": "3.2V LiFePO4 Özel Şarj Yönetim Entegresi (3.65V Kesme)",
        "DNP": "NO"
    },
    {
        "Comment": "LM66100DCKR",
        "Designator": "U6",
        "Footprint": "SC-70-6",
        "LCSC Part #": "C2869734",
        "Manufacturer": "Texas Instruments",
        "Package": "SC-70-6",
        "Description": "1.5A Kesintisiz Güç Yolu İdeal Diyot",
        "DNP": "NO"
    },
    {
        "Comment": "AP2112K-3.3TRG1",
        "Designator": "U7",
        "Footprint": "SOT-23-5",
        "LCSC Part #": "C228383",
        "Manufacturer": "Diodes Inc.",
        "Package": "SOT-23-5",
        "Description": "3.3V 600mA Düşük Gürültülü LDO Regülatör",
        "DNP": "NO"
    },
    {
        "Comment": "SN65HVD230DR",
        "Designator": "U8",
        "Footprint": "SOIC-8",
        "LCSC Part #": "C12084",
        "Manufacturer": "Texas Instruments",
        "Package": "SOIC-8",
        "Description": "3.3V CAN-Bus Alıcı-Verici (1 Mbps)",
        "DNP": "NO"
    },
    {
        "Comment": "LTV-356T",
        "Designator": "U9",
        "Footprint": "SOP-4",
        "LCSC Part #": "C1709",
        "Manufacturer": "Lite-On",
        "Package": "SOP-4",
        "Description": "3.75 kVrms Optokuplör (Boş Vites Müşür İzolasyonu)",
        "DNP": "NO"
    },
    {
        "Comment": "BTS7002-1EPP",
        "Designator": "U10",
        "Footprint": "PG-TSDSO-14-22",
        "LCSC Part #": "C534824",
        "Manufacturer": "Infineon Technologies",
        "Package": "PG-TSDSO-14",
        "Description": "2.6 mΩ 21A Akıllı Yüksek Taraf PROFET Anahtarı + Akım Algılama",
        "DNP": "NO"
    },
    {
        "Comment": "VO14642AABTR",
        "Designator": "U11, U12",
        "Footprint": "SOP-4",
        "LCSC Part #": "C2653901",
        "Manufacturer": "Vishay",
        "Package": "SOP-4",
        "Description": "Opto-MOSFET Solid-State Röle 60V 2A (Marş & Kill-Switch)",
        "DNP": "NO"
    },
    {
        "Comment": "SQJ411EP",
        "Designator": "Q1",
        "Footprint": "PowerPAK SO-8",
        "LCSC Part #": "C2681534",
        "Manufacturer": "Vishay",
        "Package": "PowerPAK SO-8",
        "Description": "P-Kanal -40V 30A Ters Polarite Koruma MOSFET",
        "DNP": "NO"
    },
    {
        "Comment": "DMN6075S",
        "Designator": "Q5",
        "Footprint": "SOT-23",
        "LCSC Part #": "C209633",
        "Manufacturer": "Diodes Inc.",
        "Package": "SOT-23",
        "Description": "N-Kanal 60V 2.5A 110 dB Siren Sürücü MOSFET",
        "DNP": "NO"
    },
    {
        "Comment": "TPSMC36A",
        "Designator": "D1",
        "Footprint": "DO-214AB (SMC)",
        "LCSC Part #": "C343277",
        "Manufacturer": "Littelfuse",
        "Package": "SMC",
        "Description": "1500W Otomotiv Geçici Gerilim Bastırıcı TVS Diyot",
        "DNP": "NO"
    },
    {
        "Comment": "PESD2CAN",
        "Designator": "D2",
        "Footprint": "SOT-23",
        "LCSC Part #": "C35282",
        "Manufacturer": "Nexperia",
        "Package": "SOT-23",
        "Description": "CAN-Bus Çift Yönlü ESD Koruma Diyotu",
        "DNP": "NO"
    },
    {
        "Comment": "USBLC6-2SC6",
        "Designator": "D3",
        "Footprint": "SOT-23-6",
        "LCSC Part #": "C7519",
        "Manufacturer": "STMicroelectronics",
        "Package": "SOT-23-6",
        "Description": "USB Type-C D+/D-/VBUS ESD Koruma Entegresi",
        "DNP": "NO"
    },
    {
        "Comment": "1812L200PR",
        "Designator": "F1",
        "Footprint": "SMD 1812",
        "LCSC Part #": "C70154",
        "Manufacturer": "Littelfuse",
        "Package": "1812",
        "Description": "2A Tutma / 4A Atma PTC Polimer Sigorta",
        "DNP": "NO"
    },
    {
        "Comment": "6.8uH (IHLP-2020)",
        "Designator": "L1",
        "Footprint": "SMD 5.2x5.2 mm",
        "LCSC Part #": "C167732",
        "Manufacturer": "Vishay / Sunlord",
        "Package": "SMD 5.2x5.2",
        "Description": "6.8 µH Korumalı Güç Bobini (4.5A Doyum)",
        "DNP": "NO"
    },
    {
        "Comment": "22uF 50V X7R",
        "Designator": "C1, C2",
        "Footprint": "SMD 1210",
        "LCSC Part #": "C15850",
        "Manufacturer": "Murata / Yageo",
        "Package": "1210",
        "Description": "Buck Giriş Filtre Seramik Kapasitörleri",
        "DNP": "NO"
    },
    {
        "Comment": "47uF 10V X7R",
        "Designator": "C3",
        "Footprint": "SMD 1210",
        "LCSC Part #": "C96985",
        "Manufacturer": "Murata / Yageo",
        "Package": "1210",
        "Description": "Buck Çıkış Filtre Seramik Kapasitörü",
        "DNP": "NO"
    },
    {
        "Comment": "100uF 10V Tantal",
        "Designator": "C4",
        "Footprint": "EIA-7343-31 (D Kılıf)",
        "LCSC Part #": "C7171",
        "Manufacturer": "AVX / KEMET",
        "Package": "7343",
        "Description": "SIM808 2A GSM RF Burst Tepe Akım Tampon Tantal",
        "DNP": "NO"
    },
    {
        "Comment": "100nF 50V X7R",
        "Designator": "C5, C7, C8",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C14663",
        "Manufacturer": "Yageo",
        "Package": "0603",
        "Description": "BOOT & RF Dekuplaj Kapasitörleri",
        "DNP": "NO"
    },
    {
        "Comment": "10uF 16V X7R",
        "Designator": "C6",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C19702",
        "Manufacturer": "Yageo",
        "Package": "0603",
        "Description": "3.3V LDO Çıkış Filtre Kapasitörü",
        "DNP": "NO"
    },
    {
        "Comment": "330R 1%",
        "Designator": "R5, R6, R7, R11, R12",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C23140",
        "Manufacturer": "Uniroyal / Yageo",
        "Package": "0603",
        "Description": "LED ve SSR Sürücü Akım Sınırlama Dirençleri",
        "DNP": "NO"
    },
    {
        "Comment": "10k 1%",
        "Designator": "R2, R4, R14, R16",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C25804",
        "Manufacturer": "Uniroyal / Yageo",
        "Package": "0603",
        "Description": "Pull-Up / Gerilim Bölücü Dirençleri",
        "DNP": "NO"
    },
    {
        "Comment": "4.7k 1%",
        "Designator": "R13, R19, R20",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C23162",
        "Manufacturer": "Uniroyal / Yageo",
        "Package": "0603",
        "Description": "PWRKEY & Sinyal Seri/Pull-Up Dirençleri",
        "DNP": "NO"
    },
    {
        "Comment": "100k 1%",
        "Designator": "R15, R17, R18",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C25803",
        "Manufacturer": "Uniroyal / Yageo",
        "Package": "0603",
        "Description": "Buck Gerilim Bölücü & Bias Dirençleri",
        "DNP": "NO"
    },
    {
        "Comment": "5.1k 1%",
        "Designator": "R8, R9",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C23186",
        "Manufacturer": "Uniroyal / Yageo",
        "Package": "0603",
        "Description": "USB Type-C CC1/CC2 Pull-Down Dirençleri",
        "DNP": "NO"
    },
    {
        "Comment": "1.2k 1%",
        "Designator": "R10",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C22775",
        "Manufacturer": "Uniroyal / Yageo",
        "Package": "0603",
        "Description": "BTS7002 IS Akım Algılama Şönt Direnci",
        "DNP": "NO"
    },
    {
        "Comment": "54.9k 1%",
        "Designator": "R1",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C23214",
        "Manufacturer": "Uniroyal / Yageo",
        "Package": "0603",
        "Description": "Giriş Gerilim Algılama Bölücü Direnci",
        "DNP": "NO"
    },
    {
        "Comment": "2.4k 1%",
        "Designator": "R3",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C23089",
        "Manufacturer": "Uniroyal / Yageo",
        "Package": "0603",
        "Description": "LiFePO4 Şarj Akım Programlama Direnci",
        "DNP": "NO"
    },
    {
        "Comment": "RED LED",
        "Designator": "LED1",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C2286",
        "Manufacturer": "Everlight",
        "Package": "0603",
        "Description": "Kırmızı Alarm Durum LED'i",
        "DNP": "NO"
    },
    {
        "Comment": "BLUE LED",
        "Designator": "LED2",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C72041",
        "Manufacturer": "Everlight",
        "Package": "0603",
        "Description": "Mavi BLE Durum LED'i",
        "DNP": "NO"
    },
    {
        "Comment": "GREEN LED",
        "Designator": "LED3",
        "Footprint": "SMD 0603",
        "LCSC Part #": "C72043",
        "Manufacturer": "Everlight",
        "Package": "0603",
        "Description": "Yeşil GSM/Hücresel Durum LED'i",
        "DNP": "NO"
    },
    {
        "Comment": "SMD Push Button",
        "Designator": "SW1, SW2",
        "Footprint": "SMD 5x5mm (KMR2)",
        "LCSC Part #": "C318884",
        "Manufacturer": "C&K / Korean HRO",
        "Package": "SMD 4P",
        "Description": "Reset (SW1) & Bootloader (SW2) Butonları",
        "DNP": "NO"
    },
    {
        "Comment": "Nano SIM Socket",
        "Designator": "J2",
        "Footprint": "SMD Push-Pull",
        "LCSC Part #": "C383794",
        "Manufacturer": "Korean HRO",
        "Package": "SMD 6P",
        "Description": "Alt Yüzey Nano SIM Kart Yuvası",
        "DNP": "NO"
    },
    {
        "Comment": "USB Type-C 16-Pin",
        "Designator": "J4",
        "Footprint": "SMD USB-C",
        "LCSC Part #": "C2765186",
        "Manufacturer": "GCT / Korean HRO",
        "Package": "SMD 16P",
        "Description": "Yerel Seri Programlama ve Telemetri Portu",
        "DNP": "NO"
    },
    {
        "Comment": "U.FL-R-SMT-1",
        "Designator": "ANT1, ANT2",
        "Footprint": "SMD 3x3mm",
        "LCSC Part #": "C14899",
        "Manufacturer": "Hirose / LCSC",
        "Package": "SMD",
        "Description": "GSM & GPS Harici Anten Konnektörleri",
        "DNP": "NO"
    },
    # DNF (Do Not Fit) / Hand Soldered Parts:
    {
        "Comment": "Molex Micro-Fit 14P (43045-1400)",
        "Designator": "J1",
        "Footprint": "Through-Hole 2x7 R/A P3.0mm",
        "LCSC Part #": "DNF (Do Not Fit - Hand Soldered)",
        "Manufacturer": "Molex",
        "Package": "Through-Hole",
        "Description": "Ana Araç Tesisat Soketi (Geliştirici tarafından el ile lehimlenecektir)",
        "DNP": "YES"
    },
    {
        "Comment": "JST-PH 2-Pin",
        "Designator": "J3",
        "Footprint": "Through-Hole R/A P2.0mm",
        "LCSC Part #": "DNF (Do Not Fit - Hand Soldered)",
        "Manufacturer": "JST",
        "Package": "Through-Hole",
        "Description": "LiFePO4 Batarya Soketi (El ile lehimlenecektir)",
        "DNP": "YES"
    },
    {
        "Comment": "M2.5 Mounting Hole",
        "Designator": "H1, H2, H3, H4",
        "Footprint": "M2.5 Pad Via",
        "LCSC Part #": "DNF (Mechanical)",
        "Manufacturer": "Standard",
        "Package": "Mechanical",
        "Description": "Şase ve Kutu Sabitleme Montaj Delikleri",
        "DNP": "YES"
    }
]

df_bom = pd.DataFrame(BOM_DATABASE)

bom_csv_path = os.path.join(PROD_DIR, "automoto_bom_jlcpcb.csv")
bom_xlsx_path = os.path.join(PROD_DIR, "automoto_bom_jlcpcb.xlsx")

df_bom.to_csv(bom_csv_path, index=False)
df_bom.to_excel(bom_xlsx_path, index=False)
print(f" -> BOM Dosyaları Oluşturuldu:\n    - CSV:  {bom_csv_path}\n    - Excel: {bom_xlsx_path}")

# 4. Teklif Talep Metni (RFQ Specification)
print("[4/5] ERKAR ve Demsay için Teklif Talep Şartnamesi (RFQ) hazırlanıyor...")
rfq_txt_path = os.path.join(PROD_DIR, "TEKLIF_TALEP_METNI.txt")
rfq_md_path = os.path.join(PROD_DIR, "RFQ_SPECIFICATION.md")

rfq_content = """# AutoMoto v4.0 — PCBA (Dizgili Baskı Devre) Fiyat Teklifi Talep Formu

Merhaba,

Aşağıda teknik detayları, Gerber, BOM ve CPL dosyaları ekte paylaşılan 4 katmanlı elektronik devre kartımız için; JLCPCB altyapısı üzerinden gümrükleme, TAREKS ve tüm yasal vergileri ödenmiş olarak Türkiye içi teslim (kapıya teslim) PCBA (SMD Dizgili) fiyat teklifinizi rica ederiz.

## 1. Kart Genel Özellikleri
- Proje Adı: AutoMoto IoT Telemetri ve Güvenlik Modülü (v4.0)
- Katman Sayısı: 4 Katman (4-Layer)
- Kart Boyutları: 80.0 mm x 55.0 mm
- Kart Kalınlığı: 1.6 mm
- Bakır Ağırlığı: 1 oz (Dış katmanlar 35 µm, İç katmanlar 35 µm)
- Yüzey Kaplaması: ENIG (Daldırma Altın) veya Standart Kurşunsuz HASL
- Lehim Maskesi (Solder Mask): Yeşil (veya Mat Siyah)
- Serigrafi (Silkscreen): Beyaz
- Minimum İz / Boşluk: 0.25 mm / 0.20 mm
- Minimum Delik Çapı: 0.30 mm drill / 0.60 mm pad
- Empedans Kontrolü: JLC04161H-7628 standart 4 katmanlı yığın (Stackup) uyumlu

## 2. Dizgi (SMT Assembly) Detayları
- Dizgi Tipi: Çift Yüzeyli SMD Dizgi (Double-Sided SMT: Top & Bottom)
- Toplam SMD Bileşen Sayısı: 56 adet
- Benzersiz Parça Sayısı: 38 kalem
- Kritik Bileşenler & LCSC Kodları:
  * ESP32-S3-WROOM-1U-N16R8 (U1): LCSC C2913204
  * SIMCom SIM808 GSM+GPS LCC-68 (U2): LCSC C126275
  * LIS3DH LGA-16 MEMS İvmeölçer (U3): LCSC C71933
  * BTS7002-1EPP PROFET Yüksek Akım Anahtarı (U10): LCSC C534824
  * VO14642AABTR Solid-State Röleler (U11, U12): LCSC C2653901
  * CN3058E LiFePO4 Şarj Entegresi (U5): LCSC C112011
  * LM66100DCKR İdeal Diyot (U6): LCSC C2869734
  * TPS54302DDCR Senkron Buck (U4): LCSC C93121
- DNF (Monte Edilmeyecek / El ile Lehimlenecek) Parçalar:
  * J1: Molex Micro-Fit 14P (43045-1400 Through-hole konnektör)
  * J3: JST-PH 2-Pin Through-hole konnektör
  * H1..H4: M2.5 Montaj delikleri

## 3. Talep Edilen Adet Seçenekleri
Lütfen aşağıdaki prototip adetleri için ayrı ayrı KDV dahil anahtar teslim (gümrük, kargo dahil) fiyat ve tahmini teslim süresi iletiniz:
- Seçenek A: 2 Adet Dizgili Kart (PCBA)
- Seçenek B: 5 Adet Dizgili Kart (PCBA)

Ek Dosyalar:
1. automoto_gerber_v4.0.zip (Gerber + Drill dosyaları)
2. automoto_bom_jlcpcb.xlsx / .csv (LCSC C-Part numaralı malzeme listesi)
3. automoto_cpl_jlcpcb.csv (Centroid / Koordinat dizgi dosyası)

İyi çalışmalar dileriz.
"""

with open(rfq_txt_path, "w", encoding="utf-8") as f:
    f.write(rfq_content)

with open(rfq_md_path, "w", encoding="utf-8") as f:
    f.write(rfq_content)

print(f" -> Teklif Metni Oluşturuldu: {rfq_txt_path}")

# 5. Master ZIP Paketi (Teklif Almak İçin E-Postaya Eklenecek Tek Dosya)
print("[5/5] Tüm dosyalar 'automoto_teklif_paketi.zip' içinde birleştiriliyor...")
master_zip_path = os.path.join(PROD_DIR, "automoto_teklif_paketi.zip")

with zipfile.ZipFile(master_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(gerber_zip_path, arcname="automoto_gerber_v4.0.zip")
    zipf.write(bom_xlsx_path, arcname="automoto_bom_jlcpcb.xlsx")
    zipf.write(bom_csv_path, arcname="automoto_bom_jlcpcb.csv")
    zipf.write(cpl_csv_path, arcname="automoto_cpl_jlcpcb.csv")
    zipf.write(rfq_txt_path, arcname="TEKLIF_TALEP_METNI.txt")

print(f"\n[OK] İŞLEM TAMAMLANDI! Master Teklif Paketi:\n -> {master_zip_path}\n")
