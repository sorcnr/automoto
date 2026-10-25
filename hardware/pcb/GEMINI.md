# KiCad PCB ve Şematik Tasarım Kuralları (Hardware Design Guardrails)

Bu dizin altındaki tüm donanım, şematik ve PCB geliştirme çalışmalarında aşağıdaki tasarım ve doğrulama protokollerine koşulsuz uyulmalıdır:

## 1. Şematik Öncelikli Çalışma Sırası (Schematic-First Protocol)
- PCB üzerinde herhangi bir yeni hat çekilmeden veya revizyon yapılmadan önce **mutlaka elektrik şeması (`.kicad_sch`)** güncellenmeli ve doğrulanmalıdır.
- Şematik üzerinde `flatpak run --command=kicad-cli org.kicad.KiCad sch erc` çalıştırılmalı ve **0 Hata, 0 Uyarı (Found 0 violations)** elde edilmeden PCB aşamasına geçilmemelidir.
- Şematik doğrulanınca SVG, PDF ve PNG görsel çizimleri dışa aktarılmalıdır.

## 2. Konnektör ve İğne Delikleri İzolasyonu (Connector Routing Safety)
- Molex, JST veya başlık tipi çok pinli Through-Hole konnektörlerin pin delikleri arasından (özellikle iki pin sırası arasındaki koridordan) **asla devre yolu geçirilmemelidir**.
- Pin çıkışları her zaman dışa doğru yönlendirilmelidir (örneğin Üst Sıra yukarı, Alt Sıra aşağı/yana).
- Delik halkaları (annular ring) çevresinde IPC-2221 standardına uygun temiz emniyet payı bırakılmalıdır.

## 3. 4-Katmanlı Yığın ve Toprak Düzlemi Mimarisi
- `In1.Cu` (İç Katman 1) her zaman **%100 kesintisiz, katı Toprak Düzlemi (GND Plane)** olarak tanımlanmalı ve bu katmana sinyal hattı sokulmamalıdır.
- Üst (`F.Cu`) ve Alt (`B.Cu`) katmanlardaki tüm SMD `GND` pedleri, bağımsız `0.3 mm / 0.6 mm` vialar ile doğrudan `In1.Cu` düzlemine bağlanmalıdır.
- Yüzey katmanları gereksiz yere bakırla doldurulmamalı; izlerin optik ve 3D incelenebilirliği korunmalıdır.
- Kendi netine veya düzlemine tek katmandan temas eden boşta dikiş viaları (`via_dangling`) kesinlikle engellenmelidir.

## 4. Headless KiCad CLI ile Otomatik Doğrulama ve Render Alma
- PCB oluşturulduktan veya düzenlendikten sonra derhal aşağıdaki komutlarla doğrulanmalıdır:
  1. **DRC Testi:** `flatpak run --command=kicad-cli org.kicad.KiCad pcb drc --output drc_report.rpt automoto.kicad_pcb`
     *(Kabul kriteri: 0 DRC violations, 0 unconnected pads).*
  2. **2D Kırpılmış SVG Export:** `flatpak run --command=kicad-cli org.kicad.KiCad pcb export svg --page-size-mode 2 --exclude-drawing-sheet --mode-single ...`
  3. **Rasterizasyon:** `inkscape -w 2400 --export-background=white --export-filename=...`
  4. **3D Raytracing Renderları:** `flatpak run --command=kicad-cli org.kicad.KiCad pcb render --side top/bottom --quality high ...`
