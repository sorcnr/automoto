# AutoMoto — ESP32 & LTE Tabanlı Akıllı Motosiklet Güvenlik ve Telemetri Sistemi

## 1. Proje Özeti ve Vizyonu
AutoMoto, modern ve klasik motosikletler için geliştirilen; ESP32-S3 mimarisini, düşük güç tüketimli hücresel LTE bağlantısını (LTE-M/NB-IoT), BLE 5.0/6.0 yakınlık algılamasını ve MQTT tabanlı bulut haberleşmesini tek bir kompakt gövdede birleştiren yeni nesil bir akıllı güvenlik, uzaktan yönetim ve telemetri platformudur.

Sistem, geleneksel takip cihazlarının pasif yapısını aşarak; anahtarsız biniş (Keyless Go), sınırsız menzilli uzaktan çalıştırma (Remote Start), sürüş emniyet kilitli uzaktan motor durdurma (Remote Kill Switch), darbe ve kaldırma alarmı ile harici güç sabotajlarına karşı dahili $LiFePO_4$ batarya koruması sunar.

## 2. Temel Fonksiyonel Özellikler

### 2.1. Güvenlik ve Hırsızlık Önleme (Alarm & Sabotaj Koruması)
- **MEMS Hareket / Darbe Algılama:** STMicroelectronics LIS3DH ultra düşük güç tüketimli 3 eksenli ivmeölçer ile motosikletin sehpaya alınması, dik konuma getirilmesi, kurcalanması veya çekiciye yüklenmesi anlık donanımsal kesme (Interrupt) ile algılanır.
- **Dahili Siren Sürücüsü:** 110 dB su geçirmez piezo siren ve flaşör ikaz çıkışı.
- **Sabotaj Korumalı Dahili Batarya:** Ana motosiklet aküsü sökülse veya kabloları kesilse dahi sistem otomatik olarak dahili LiFePO4 bataryaya geçerek çalışmaya devam eder ve sunucuya anlık alarm iletir.

### 2.2. BLE Keyless Go (Yakınlık Tabanlı Anahtarsız Giriş)
- **Otomatik Kontak Açma / Kapama:** Sürücü akıllı telefonuyla motosiklete yaklaştığında (tanımlı RSSI ve güvenlik eşiği aşıldığında) kontak otomatik olarak açılır. Sürücü uzaklaştığında kontak kapanır ve alarm kurulur.
- **Röle Saldırısı (Anti-Relay) Koruması:** Salt RSSI gücüne güvenilmez; dinamik challenge-response (zaman damgalı dönen anahtar) doğrulaması ile RF sinyal uzatıcılarla yapılan hırsızlıklar engellenir.

### 2.3. Uzaktan Kontrol ve Telemetri (LTE & MQTT)
- **Sınırsız Menzilli Uzaktan Çalıştırma (Remote Start):** Mobil uygulama üzerinden verilen komutla kontak açılır ve marş rölesi tetiklenir.
- **Emniyet Kilitli Uzaktan Motor Durdurma (Kill Switch):** Çalınma durumunda motor uzaktan stop edilir. Arka tekerlek kilitlenmesini engellemek için doğrudan kontak kesilmez; yan ayak müşürü hattı üzerinden ECU kontrollü şekilde durdurulur ve sürüş halinde devreye girmemesi için IMU hız kontrolü yapılır.
- **Canlı GPS / GNSS Takibi & Geofence:** Sanal coğrafi çit dışına çıkıldığında harita üzerinden anlık izleme ve bildirim.

## 3. Donanım Mimarisi ve Bileşenler

```
                        +----------------------------+
                        | Motosiklet Aküsü (12V DC)  |
                        +--------------+-------------+
                                       |
                   [TVS Diyot & Buck Regülatör (5V/3.3V)]
                                       |
            +--------------------------+--------------------------+
            |                          |                          |
+-----------v-----------+  +-----------v-----------+  +-----------v-----------+
| LiFePO4 Şarj Entegresi|  | ESP32-S3 Mikrodenetici|  | LTE Modem (SIM7080G)  |
| (CN3058 / TP4056)     |  | - Xtensa Dual-Core    |  | - LTE-M / NB-IoT      |
| + 1S 18650 Batarya    |  | - BLE 5.0 / ULP Core  |  | - Entegre GNSS / GPS  |
+-----------------------+  +-----------+-----------+  +-----------+-----------+
                                       |                          |
       +-------------------------------+--------------------------+
       | (I2C)                         | (UART / RI Kesmesi)
+------v------+                +-------v----------------------------------+
| LIS3DH IMU  |                | Röle & Sürücü Katmanı (Opto-İzole)       |
| İvmeölçer   |                | - CH1: Kontak Ana Rölesi                 |
+-------------+                | - CH2: Marş Rölesi (Boş Vites Kilitli)   |
                               | - CH3: Emniyet Kesici (Yan Ayak Hattı)   |
                               | - CH4: 110 dB Siren & Flaşör Sürücüsü    |
                               +------------------------------------------+
```

### 3.1. Bileşen Tablosu

| Modül | Seçilen Donanım | Görevi / Çalışma Parametreleri |
| :--- | :--- | :--- |
| Ana İşlemci | ESP32-S3-WROOM-1 | 240 MHz Dual-Core, BLE 5.0, ULP yardımcı çekirdek, yerel USB |
| Hücresel & GNSS | SIMCom SIM808 | Quad-Band GSM/GPRS + entegre 22-kanal GPS alıcısı (U.FL harici anten) |
| Hareket Sensörü | STMicroelectronics LIS3DH | 3 eksen MEMS ivmeölçer, I2C arayüzü, donanımsal hareket kesmesi |
| Dahili Batarya | 1S LiFePO4 18650 (3.2V 1500mAh) | $-20^\circ\text{C}$ ile $+70^\circ\text{C}$ operasyon, yüksek termal kararlılık |
| Güç Yönetimi | TPS54302 Buck + AP2112K LDO + CN3058 + LM66100 | 12V $\to$ 3.86V Buck (3A), 3.3V LDO, LiFePO4 şarj ve kesintisiz ideal diyot |
| Katı-Hal Anahtarlama | PROFET & Solid-State Röleler (Mekanik Rölesiz) | Kontak: BTS7002-1EPP (25A PROFET + IS akım algılama), Marş: VO14642AAB (SSR), Kill Switch: VO14642AAB (SSR), Siren: DMN6075S (N-FET) |
| Euro 5 CAN (Ops.) | SN65HVD230 Alıcı-Verici | ISO 19689 6 pin teşhis soketinden telemetri ve vites okuma |

## 4. Güç Yönetimi ve Hibrit Uyandırma Mimarisi
Motosiklet aküsünün tükenmemesi için sistem park halindeyken agresif bir derin uyku (Deep Sleep) stratejisi uygular. Akım çekişi uykudayken $100\,\mu\text{A}$ seviyesinin altındadır.

### Çift Kaynaklı Uyandırma Mantığı (Unified Wakeup Logic)
- **Periyodik BLE Taraması (Keyless Go):** ESP32'nin dahili RTC zamanlayıcısı sistemi her 1.5 saniyede bir uyandırır. 40-50 milisaniye süreyle BLE taraması yapılır. Yetkili telefon algılanırsa kontak açılır; algılanmazsa derhal derin uykuya dönülür.
- **Hücresel Asenkron Kesme (Uzaktan Kontrol):** LTE modem PSM/eDRX modunda bekler. Kullanıcı buluttan veya VPS'ten MQTT komutu gönderdiğinde modem paketi alır ve RI (Ring Indicator) pinini LOW seviyesine çeker. Bu sinyal ESP32'nin EXT0 RTC GPIO pinini tetikleyerek çipi nanosaniyeler içinde uyandırır.
- **Fiziksel Sarsıntı Kesmesi (Alarm):** LIS3DH sensörü hareket algıladığı anda INT pini üzerinden ESP32'nin EXT1 RTC GPIO pinini tetikler. Sistem uyanarak acil durum konumunu MQTT üzerinden yayınlar ve sireni çalar.

## 5. MQTT ve Bulut / VPS Haberleşme Mimarisi
Haberleşme omurgası; kendi sunucunuzda barındırılan bir VPS (Mosquitto / EMQX) veya yönetilen bulut broker'ı (AWS IoT Core / HiveMQ) üzerine kurulur. Tüm haberleşme TLS v1.3 ile şifrelenir (Port 8883).

### 5.1. MQTT Topic (Konu) Hiyerarşisi
Cihaz bazlı benzersiz kimlik: `{device_id}` (Örn: `ESP32_A8B6C4`)

- **Telemetri Verileri (Device $\to$ Broker):**
  - **Konu:** `automoto/{device_id}/telemetry`
  - **Açıklama:** Periyodik akü durumu, GPS koordinatları, şebeke sinyal gücü, sistem sıcaklığı.
- **Olay ve Güvenlik Alarmları (Device $\to$ Broker):**
  - **Konu:** `automoto/{device_id}/events`
  - **Açıklama:** Sarsıntı algılandı, ana güç kesildi (sabotaj), kaza/düşme algılandı.
- **Uzaktan Komut Alma (Broker $\to$ Device):**
  - **Konu:** `automoto/{device_id}/commands`
  - **Açıklama:** Mobil uygulamadan gönderilen çalıştırma, durdurma ve alarm aç/kapa talimatları.
- **Komut Yanıtları (Device $\to$ Broker):**
  - **Konu:** `automoto/{device_id}/response`
  - **Açıklama:** Alınan komutun icra edilme durumu ve hata bildirimleri.
- **Bağlantı Durumu / LWT (Last Will and Testament):**
  - **Konu:** `automoto/{device_id}/status`
  - **Payload:** `{"status": "online"}` veya `{"status": "offline"}` (QoS 1, Retained).

### 5.2. Standart JSON Veri Formatları

#### Telemetri Paketi (`telemetry`)
```json
{
  "ts": 1776601200,
  "device_id": "ESP32_A8B6C4",
  "battery": {
    "bike_voltage": 12.62,
    "internal_voltage": 3.28,
    "charging": true
  },
  "gnss": {
    "lat": 38.4237,
    "lng": 27.1428,
    "speed_kmh": 0.0,
    "satellites": 11,
    "fixed": true
  },
  "system": {
    "rssi_gsm": -68,
    "state": "ARMED",
    "ignition": false
  }
}
```

#### Komut Paketi (`commands`)
```json
{
  "cmd_id": "req-98214",
  "action": "REMOTE_START",
  "params": {
    "ignition": true,
    "starter_crank_ms": 1200,
    "force": false
  },
  "token": "e8f7a1c0d45..."
}
```

#### Komut Yanıtı (`response`)
```json
{
  "cmd_id": "req-98214",
  "status": "SUCCESS",
  "message": "Engine cranked successfully. Neutral gear confirmed.",
  "execution_time_ms": 1420
}
```

## 6. Sürüş Güvenliği ve Donanımsal Kilitler (Fail-Safe)
- **Boş Vites Kilidi (Neutral Interlock):** Marş rölesi tetikleme devresi, motosikletin boş vites müşürüne (Neutral Switch) donanımsal veya mantıksal olarak seri bağlıdır. Araç vitesteyken uzaktan marş komutu gelse dahi marş motoruna asla enerji verilmez.
- **Sürüş Esnasında Emniyet Kapatma Koruması:** Sürüş anında yanlışlıkla veya kötü niyetli komutla motorun stop edilmesini önlemek amacıyla, IMU sensöründen titreşim ve hız verisi okunur. Araç hareket halindeyken uzaktan emniyet kapatma devreye alınmaz; aracın hızı sıfıra inip durana kadar komut kuyrukta bekletilir.
- **Varsayılan Güvenli Durum (Default Safe):** ESP32'nin enerjisi kesilirse veya kilitlenirse tüm röleler pasif (Normally Open) konumda kalır; motosikletin sürüş dinamiklerini tehlikeye sokacak beklenmedik kısa devreler engellenir.

## 7. Proje Dosya ve Dizin Yapısı
```
automoto/
├── hardware/                  # Donanım ve Elektronik Tasarım
│   ├── schematics/            # KiCad şematik dosyaları
│   ├── pcb/                   # PCB yerleşim, spesifikasyonlar (PCB_SPECIFICATION.md) ve Gerber çıktıları
│   └── bom/                   # Malzeme Listesi (BOM tablosu)
├── firmware/                  # ESP32 Kaynak Kodları (ESP-IDF / PlatformIO)
│   ├── include/               # Başlık dosyaları
│   │   ├── ble_keyless.h      # BLE ve Challenge-Response yönetimi
│   │   ├── modem_sim7080.h    # LTE-M / GPS UART ve AT sürücüsü
│   │   ├── mqtt_handler.h     # MQTT istemcisi ve payload işleyici
│   │   ├── power_manager.h    # Deep sleep ve RTC kesme yapılandırması
│   │   └── sensors_imu.h      # LIS3DH I2C ve hareket algılama
│   ├── src/
│   │   ├── main.cpp
│   │   └── ...
│   └── platformio.ini
├── server/                    # VPS & Bulut Altyapısı
│   ├── docker-compose.yml     # Mosquitto Broker + API Gateway + DB
│   ├── mosquitto/
│   │   └── config/mosquitto.conf
│   └── certs/                 # TLS sertifikaları ve yetkilendirme anahtarları
├── mobile-app/                # Flutter / React Native Mobil Uygulama
│   ├── lib/
│   │   ├── ble/               # BLE yakınlık ve kimlik doğrulama
│   │   └── mqtt/              # Uzaktan komut ve harita takibi
├── docs/                      # Kurulum, PIN şemaları ve test kılavuzları
├── LICENSE
├── README.md
└── PROJECT.md
```

## 8. Geliştirme Yol Haritası (Roadmap)
- [ ] **Faz 1: Sistem Mimarisi ve Donanım Tasarımı:** Güç yolu, LiFePO4 şarj entegrasyonu, TVS korumaları ve 4 katmanlı PCB prototipi.
- [ ] **Faz 2: Güç Yönetimi ve Kesme Çekirdeği:** LIS3DH hareket kesmesi, SIM7080G RI bacağı üzerinden harici uyandırma ve bekleme akımının $100\,\mu\text{A}$ altına çekilmesi.
- [ ] **Faz 3: BLE Keyless Go Entegrasyonu:** Dynamic challenge-response el sıkışması ve otomatik kontak tetikleme testleri.
- [ ] **Faz 4: LTE Modem & MQTT Yığını:** SIM7080G AT komut sürücüsünün yazılması, VPS üzerindeki EMQX/Mosquitto broker'ına TLS ile bağlanılması ve çift yönlü JSON veri akışı.
- [ ] **Faz 5: Emniyet Kilitleri ve Saha Testleri:** Boş vites algılama donanımı, yan ayak emniyet kesicisi saha testleri ve titreşim/su geçirmezlik (IP67) testleri.
- [ ] **Faz 6: Euro 5 (ISO 19689) Tak-Çalıştır Soket Adaptasyonu:** CAN-bus üzerinden doğrudan veri toplama ve kablo kesmeden montaj desteği.
