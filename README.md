# AutoMoto — Akıllı Motosiklet Telemetri, Güvenlik ve Keyless Go Sistemi

AutoMoto; ESP32-S3 mimarisi, SIMCom SIM808 GSM/GPRS + GPS hücresel modülü, BLE 5.0 yakınlık algılaması (Keyless Go) ve otomotiv sınıfı katı-hal (`PROFET` / `SSR`) anahtarlama teknolojisine dayanan yeni nesil bir akıllı motosiklet telemetri ve güvenlik platformudur.

## Proje ve Tasarım Dokümantasyonu

* **Proje Genel Tanımı ve Sistem Mimarisi:** [PROJECT.md](file:///home/sorcnr/Documents/automoto/PROJECT.md)
* **PCB & Şematik Teknik İmalat Şartnamesi (v4.0):** [hardware/pcb/PCB_SPECIFICATION.md](file:///home/sorcnr/Documents/automoto/hardware/pcb/PCB_SPECIFICATION.md)

---

## Donanım ve CAD Dosyaları (`hardware/pcb/`)

* **KiCad 10 Elektrik Şematik:** [hardware/pcb/automoto.kicad_sch](file:///home/sorcnr/Documents/automoto/hardware/pcb/automoto.kicad_sch)
* **KiCad 10 4-Katmanlı PCB:** [hardware/pcb/automoto.kicad_pcb](file:///home/sorcnr/Documents/automoto/hardware/pcb/automoto.kicad_pcb)
* **Özel Sembol Kütüphanesi:** [hardware/pcb/automoto.kicad_sym](file:///home/sorcnr/Documents/automoto/hardware/pcb/automoto.kicad_sym)
* **Şematik ve PCB Üreteç Betikleri:**
  * [hardware/pcb/generate_kicad_sch.py](file:///home/sorcnr/Documents/automoto/hardware/pcb/generate_kicad_sch.py)
  * [hardware/pcb/generate_kicad_pcb.py](file:///home/sorcnr/Documents/automoto/hardware/pcb/generate_kicad_pcb.py)
* **Doğrulama Raporları:**
  * [hardware/pcb/erc_report.rpt](file:///home/sorcnr/Documents/automoto/hardware/pcb/erc_report.rpt) (ERC: 0 Violations)
  * [hardware/pcb/drc_report.rpt](file:///home/sorcnr/Documents/automoto/hardware/pcb/drc_report.rpt) (DRC: 0 Violations, 0 Unconnected Pads)

### Görsel Çıktılar

* **Şematik Çizimi:** [hardware/pcb/drawings/automoto_schematic.png](file:///home/sorcnr/Documents/automoto/hardware/pcb/drawings/automoto_schematic.png) | [PDF](file:///home/sorcnr/Documents/automoto/hardware/pcb/drawings/automoto_schematic.pdf)
* **2D PCB Yerleşimi:** [hardware/pcb/drawings/automoto_pcb.png](file:///home/sorcnr/Documents/automoto/hardware/pcb/drawings/automoto_pcb.png) | [SVG](file:///home/sorcnr/Documents/automoto/hardware/pcb/drawings/automoto_pcb.svg)
* **3D Raytracing Renderları:**
  * [hardware/pcb/renders/kicad_3d_isometric.png](file:///home/sorcnr/Documents/automoto/hardware/pcb/renders/kicad_3d_isometric.png)
  * [hardware/pcb/renders/kicad_3d_top.png](file:///home/sorcnr/Documents/automoto/hardware/pcb/renders/kicad_3d_top.png)
  * [hardware/pcb/renders/kicad_3d_bottom.png](file:///home/sorcnr/Documents/automoto/hardware/pcb/renders/kicad_3d_bottom.png)
