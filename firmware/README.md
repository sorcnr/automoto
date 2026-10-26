# AutoMoto — ESP32-S3 Firmware Geliştirme Kılavuzu

Bu dizin, AutoMoto akıllı motosiklet güvenlik ve telemetri sisteminin **ESP32-S3 (ESP-IDF v5.x / PlatformIO)** kaynak kodlarını içerir.

Proje, hem **PlatformIO** (VS Code kolaylığı ve CI/CD için) hem de resmi **ESP-IDF CLI (`idf.py`)** (Secure Boot v2, Flash Encryption ve eFuse kilitleri için) ile doğrudan derlenebilecek hibrit bir mimaride yapılandırılmıştır.

---

## 1. Dizin ve Dosya Yapısı

```
firmware/
├── platformio.ini           # PlatformIO proje yapılandırması (src_dir = main)
├── CMakeLists.txt           # Kök CMakeLists (ESP-IDF idf.py için)
├── sdkconfig.defaults       # NimBLE, TWDT, OTA Rollback, 16MB Flash ayarları
├── partitions.csv           # Secure Boot v2 (48KB bootloader) + Çift OTA + Şifreli Depolama
├── SECURITY_SPECIFICATION.md# Güvenlik, mTLS, eFuse ve Anti-Relay şartnamesi
├── main/
│   ├── CMakeLists.txt       # Ana bileşen CMake tanımı
│   ├── main.c               # app_main, OTA doğrulama ve çift çekirdek FreeRTOS görevleri
│   ├── board_pins.h / .c    # PCB v4.0 donanım pinleri ve GPIO başlatıcı
│   ├── actuator_safety.h / .c # [YENİ] Donanımsal Watchdog (TWDT) denetimli aktüatör mimarisi
│   ├── failsafe.h / .c      # 3 aşamalı Soft-Kill ve boş vites marş kilidi
│   ├── power_manager.h / .c # Derin uyku, RTC uyanma ve güç tasarrufu
│   ├── ble_keyless.h / .c   # Apache NimBLE Keyless Go ve RTT (Anti-Relay) ölçümü
│   ├── sensors_imu.h / .c   # LIS3DH MEMS ivmeölçer I2C sürücüsü
│   └── modem.h / .c         # Hücresel Modem HAL (SIM808 & Quectel EG915U)
└── README.md
```

---

## 2. Kritik Güvenlik ve Emniyet Mimarisi

### 2.1. Donanımsal Task Watchdog Timer (TWDT) & Aktüatör Görevi
- **İzolasyon:** Marş rölesi (`U11`), kontak PROFET'i (`U10`) ve Soft-Cut SSR'si (`U12`) genel ağ veya telemetri görevlerinden tamamen izole edilmiştir.
- **Yüksek Öncelik:** Core 0 üzerinde `configMAX_PRIORITIES - 2` seviyesinde koşturulur.
- **Donanımsal Bekçi (TWDT):** Görev her 20 ms'de bir `esp_task_wdt_reset()` ile beslenir. Eğer sistem kilitlenirse, donanımsal watchdog anında panic üreterek tüm röleleri 0 (açık / güvenli pasif) seviyesine çeker ve çipi resetler.
- **Marş Hard-Limit (1500 ms):** Marş motorunun takılı kalıp yanmasını veya aküyü bitirmesini engellemek için, yazılımdan iptal komutu gelmese bile aktüatörün bağımsız zamanlayıcısı marşı **en geç 1500 ms içinde zorla keser**.

### 2.2. Secure Boot v2 ve Flash Encryption Hazırlığı
- **48 KB Bootloader Marjı:** `partitions.csv` içinde partition table offset'i `0xC000` olarak ayarlanmış ve ilk partition `0x10000` sonrasına yerleştirilmiştir. Böylece RSA-3072 imzalı Secure Boot v2 bootloader'ı için gerekli 32-48 KB alan ilk günden ayrılmıştır.
- **Şifreli Partisyonlar:** `nvs_keys` ve `storage` partisyonlarına `encrypted` bayrağı tanımlanarak donanımsal AES-XTS şifreleme altyapısı hazırlandı.

### 2.3. Otonom OTA Rollback (Tuğlalaşma Önleme)
- Sistem `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` ile yapılandırılmıştır.
- Uzaktan hücresel ağ üzerinden yeni firmware yüklendiğinde, bootloader yeni uygulamayı `ESP_OTA_IMG_PENDING_VERIFY` durumunda açar.
- Yeni sürüm tüm donanım testlerini (GPIO, IMU, Modem, Aktüatörler) başarıyla tamamlayıp `esp_ota_mark_app_valid_cancel_rollback()` çağırmadan çöker veya bootloop'a girerse; bootloader sonraki yeniden başlatmada **otomatik olarak önceki çalışan firmware slotuna (ota_0 / ota_1) geri döner**.

---

## 3. Derleme ve Yükleme Seçenekleri

### Seçenek 1: PlatformIO ile Derleme (Önerilen Günlük Geliştirme)
```bash
cd firmware
pio run
pio run -t upload -t monitor
```

### Seçenek 2: Doğrudan ESP-IDF (`idf.py`) ile Derleme (Seri Üretim & Güvenlik)
```bash
cd firmware
idf.py set-target esp32s3
idf.py menuconfig
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

---

## 4. Donanım Pin Eşleşmeleri Özeti (PCB v4.0)

| GPIO | Net Adı | Fonksiyon |
| :--- | :--- | :--- |
| **GPIO 1, 2** | `I2C_SDA`, `I2C_SCL` | LIS3DH MEMS İvmeölçer |
| **GPIO 3** | `SSR_KILL` | U12: VO14642AAB Motor Ateşleme Kesici (Soft-Cut) |
| **GPIO 8** | `PROFET_IN` | U10: BTS7002-1EPP 25A Kontak Anahtarı |
| **GPIO 9** | `SSR_STARTER` | U11: VO14642AAB Marş Basma SSR (Boş Vites Kilitli) |
| **GPIO 10** | `PROFET_IS` | BTS7002 Kontak Akımı ADC Algılama |
| **GPIO 11** | `SIREN_CTRL` | Q5: DMN6075S 110 dB Piezo Siren Sürücüsü |
| **GPIO 12** | `SENSE_NEUTRAL` | U9: LTV-356T Boş Vites Algılama |
| **GPIO 17, 18** | `MODEM_TX`, `MODEM_RX`| SIM808 / Quectel EG915U AT Komut UART |
| **GPIO 21, 38** | `STATUS`, `PWRKEY` | Hücresel Modem Güç ve Durum Hatları |
| **GPIO 46..48** | `LED_GSM`, `ALARM`, `BLE`| Sistem Durum Göstergeleri |
