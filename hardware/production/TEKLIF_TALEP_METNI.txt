# AutoMoto v4.0 — PCBA (Dizgili Baskı Devre) Fiyat Teklifi Talep Formu

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
