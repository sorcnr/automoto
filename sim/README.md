# AutoMoto v4.0 — Simülasyon Ortamı Kılavuzu

Bu dizin, **AutoMoto v4.0 (ESP32-S3 + SIM808 + Katı-Hal PROFET/SSR)** donanım revizyonu için geliştirilmiş uçtan uca simülasyon ortamlarını barındırır. Fiziksel kart, antenler ve motosiklet bağlantıları masada olmadan tüm sistem mantığını doğrulayabilirsiniz.

---

## 1. Mimarideki Simülasyon Katmanları

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AutoMoto v4.0 Simülasyonu                      │
├──────────────────────────────────┬─────────────────────────────────────┤
│      1. Sistem Emülasyonu        │        2. Sanal Modem Mock          │
│            (Renode)              │           (Python SIM808)           │
│  - ESP32-S3 Xtensa Çekirdek      │  - AT Komut Yanıtlayıcı            │
│  - USB JTAG/UART0 Konsolu        │  - Dinamik GPS (NMEA/CGNSINF)       │
│  - Modem UART1 (TCP Port 4321)   │  - GPRS & Şebeke Kayıt Durumu       │
├──────────────────────────────────┼─────────────────────────────────────┤
│      3. Görsel İnteraktif        │        4. Euro 5 CAN-Bus            │
│            (Wokwi)               │           (Linux SocketCAN)         │
│  - BTS7002 PROFET (Kontak)       │  - Sanal CAN Portu (vcan0)          │
│  - VO14642AAB SSR (Marş & Stop)  │  - Motor Devir & Hız Paketleri      │
│  - Durum LED'leri (Alarm/BLE/GSM)│  - Boş Vites & Müşür Simülasyonu    │
└──────────────────────────────────┴─────────────────────────────────────┘
```

---

## 2. Renode ile Firmware Simülasyonu

Renode platform tanımı ([automoto.repl](file:///home/sorcnr/Documents/automoto/sim/renode/automoto.repl)) ve çalıştırma betiği ([automoto.resc](file:///home/sorcnr/Documents/automoto/sim/renode/automoto.resc)) v4.0 PCB şartnamesine birebir uygundur.

### Başlatma

* **Grafik Arayüz (GUI) ile:**
  ```bash
  renode sim/renode/automoto.resc
  ```
* **Terminal / Konsol (Headless) Modunda:**
  ```bash
  renode --console -P -1 sim/renode/automoto.resc
  ```
  *(veya pratik başlatıcıyı kullanabilirsiniz: `./sim/run_renode.sh`)*

### Firmware Yükleme ve Çalıştırma
Renode monitor istemcisinde (`(automoto)`):
```text
(automoto) sysbus LoadELF @firmware/.pio/build/esp32s3/firmware.elf
(automoto) start
```

---

## 3. Sanal SIM808 GSM/GPRS + GPS Modemi (`mock_sim808.py`)

Renode üzerindeki `uart1` modülü `127.0.0.1:4321` TCP portunu dinler. Sanal modem scriptini çalıştırarak gerçek bir SIM808 gibi davranmasını sağlayabilirsiniz:

```bash
python3 sim/tools/mock_sim808.py
```

### Yetenekleri:
- `AT+CPIN?` $\to$ `+CPIN: READY`
- `AT+CSQ` $\to$ Sinyal kalitesi (`+CSQ: 28,0`)
- `AT+CREG?` / `AT+CGREG?` $\to$ GSM ve GPRS şebeke kaydı
- `AT+CGNSPWR=1` & `AT+CGNSINF` $\to$ Gerçekçi GNSS uydu kilitlenmesi, hız ve koordinat verisi
- `AT+CBC` $\to$ Akü / batarya gerilimi ölçüm cevabı

---

## 4. Wokwi ile Görsel Simülasyon (`sim/wokwi/diagram.json`)

VS Code içerisindeki **Wokwi Simulator** eklentisiyle `sim/wokwi/diagram.json` dosyasını açtığınızda:
- **GPIO 47 (Kırmızı LED):** Hırsızlık / Sarsıntı Alarmı
- **GPIO 48 (Mavi LED):** BLE Keyless Durumu
- **GPIO 46 (Yeşil LED):** GSM/GPRS Bağlantı Durumu
- **GPIO 8 (Röle/PROFET):** 25A Ana Kontak Çıkışı
- **GPIO 9 (Röle/SSR):** Marş Solenoid Tetiklemesi
- **GPIO 3 (Röle/SSR):** Kill-Switch Emniyet Kesicisi
- **GPIO 11 (Buzzer):** 110 dB Piezo Siren
- **GPIO 12 (Yeşil Buton):** Boş Vites Müşürü (Neutral Switch)
- **GPIO 4 (Kırmızı Buton):** LIS3DH Hareket/Sarsıntı Kesmesi
doğrudan interaktif olarak kontrol edilebilir.
