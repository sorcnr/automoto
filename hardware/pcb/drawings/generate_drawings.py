#!/usr/bin/env python3
"""
AutoMoto - PCB Teknik Çizim ve Şematik Üretici (Denetim Sonrası Optimize Edilmiş CAD)
Tüm 41 bileşen (3 flyback diyotu dahil) ve 4 montaj deliği revize CPL tablosuna göre çizilir.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch
import numpy as np

OUTPUT_DIR = "/home/sorcnr/Documents/automoto/hardware/pcb/drawings"
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.family'] = 'sans-serif'

def generate_floorplan():
    fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    ax.set_xlim(-16, 102)
    ax.set_ylim(-16, 72)
    ax.set_aspect('equal')

    # Grid
    ax.grid(True, which='both', color='#21262d', linestyle='--', linewidth=0.5, alpha=0.7)
    ax.set_xticks(np.arange(-10, 100, 5))
    ax.set_yticks(np.arange(-10, 70, 5))
    ax.tick_params(colors='#8b949e', labelsize=8)

    # 1. PCB Gövdesi (85.0 x 55.0 mm, R=3.0 mm)
    pcb_box = FancyBboxPatch(
        (0, 0), 85.0, 55.0,
        boxstyle="round,pad=0,rounding_size=3.0",
        facecolor='#161b22', edgecolor='#30363d', linewidth=2.0, zorder=2
    )
    ax.add_patch(pcb_box)

    # 2. Montaj Delikleri (M3: H1, H2, H3, H4) + 7mm Vida Başı Serbestlik Çemberleri
    hole_coords = [
        (4.0, 51.0, "H3 (4, 51)"),
        (81.0, 51.0, "H4 (81, 51)"),
        (4.0, 4.0, "H1 (4, 4)"),
        (81.0, 4.0, "H2 (81, 4)")
    ]
    for x, y, label in hole_coords:
        # 7mm Vida pulu keepout alanı (kesikli çizgi)
        washer = Circle((x, y), 3.5, facecolor='none', edgecolor='#f0883e', linestyle=':', linewidth=0.8, zorder=3)
        ax.add_patch(washer)
        pad = Circle((x, y), 3.0, facecolor='#d29922', edgecolor='#f0883e', linewidth=0.8, alpha=0.35, zorder=3)
        ax.add_patch(pad)
        hole = Circle((x, y), 1.6, facecolor='#0d1117', edgecolor='#f0883e', linewidth=1.2, zorder=4)
        ax.add_patch(hole)
        ax.plot([x-2.2, x+2.2], [y, y], color='#f0883e', linewidth=0.6, zorder=5)
        ax.plot([x, x], [y-2.2, y+2.2], color='#f0883e', linewidth=0.6, zorder=5)
        ax.text(x, y - 4.5, label.split()[0], color='#f0883e', fontsize=7, fontweight='bold', ha='center', zorder=6)

    # 3. Optimize Anten Boşaltma Bölgesi (X: 10.0-28.0, Y: 48.0-55.0) - H3 Vidasından 6mm açık
    ko = Rectangle((10.0, 48.0), 18.0, 7.0, facecolor='#f8514918', edgecolor='#f85149',
                   linestyle='--', linewidth=1.2, zorder=3)
    ax.add_patch(ko)
    ax.text(19.0, 51.5, "BLE ANTEN BOŞALTMA (KEEPOUT)\n(H3 vidasından 6 mm güvenli mesafe)", color='#f85149', fontsize=6.0, fontweight='bold', ha='center', va='center', zorder=6)

    # 4. Donanım Bileşenleri Çizimi
    def draw_chip(x, y, w, h, ref, val, color='#58a6ff', bg='#21262d'):
        rx, ry = x - w/2, y - h/2
        box = Rectangle((rx, ry), w, h, facecolor=bg, edgecolor=color, linewidth=0.9, zorder=5)
        ax.add_patch(box)
        ax.text(x, y + 0.3, ref, color=color, fontsize=6.5, fontweight='bold', ha='center', va='center', zorder=7)
        if val:
            ax.text(x, y - h/2 - 1.2, val, color='#8b949e', fontsize=5.0, ha='center', va='top', zorder=7)

    # U1: ESP32-S3 (19, 40) - Sağa kaydırıldı
    draw_chip(19.0, 40.0, 18.0, 25.5, "U1: ESP32-S3", "16MB Flash, 8MB PSRAM", color='#58a6ff', bg='#1f242c')
    ax.add_patch(Rectangle((11.0, 28.5), 16.0, 17.0, facecolor='#30363d', edgecolor='#8b949e', linewidth=0.6, zorder=6))
    ax.text(19.0, 37.0, "ESP32-S3-WROOM-1-N16R8\nXtensa Dual-Core 240MHz", color='#e6edf3', fontsize=5.8, fontweight='bold', ha='center', va='center', zorder=8)

    # J4: Type-C (36, 53.5) & D3: USBLC6-2SC6 (36, 49)
    draw_chip(36.0, 53.5, 9.0, 5.0, "J4: Type-C", "16-Pin USB (36, 53.5)", color='#58a6ff', bg='#30363d')
    draw_chip(36.0, 49.0, 3.0, 2.5, "D3", "USBLC6-2", color='#58a6ff')

    # Optimize Edilmiş Giriş Koruması (J1 Molex'in hemen arkasında: F1, D1, Q1)
    draw_chip(38.0, 10.0, 4.5, 3.2, "F1", "2A PTC", color='#a371f7')
    draw_chip(44.0, 10.0, 5.0, 4.0, "D1", "TVS 1500W", color='#a371f7')
    draw_chip(50.0, 10.0, 6.0, 5.0, "Q1: P-FET", "SQJ411EP", color='#a371f7')

    # Buck Katmanı: C1, C2, U4, L1, C3
    draw_chip(65.5, 45.0, 3.2, 2.5, "C1", "22uF", color='#a371f7')
    draw_chip(67.0, 42.5, 3.2, 2.5, "C2", "22uF", color='#a371f7')
    draw_chip(62.0, 44.0, 5.0, 4.0, "U4: Buck", "TPS54302 (3.86V)", color='#a371f7')
    draw_chip(54.0, 44.0, 10.0, 10.0, "L1: Bobin", "MSS1038 6.8uH", color='#d29922')
    draw_chip(49.0, 44.0, 3.2, 2.5, "C3", "47uF", color='#a371f7')

    # U7: LDO (48, 36)
    draw_chip(48.0, 36.0, 3.0, 3.0, "U7: LDO", "AP2112K-3.3V", color='#58a6ff')

    # SW1, SW2: Butonlar (H3 vidasından uzaklaştırıldı: 4, 43.5 ve 4, 38.5)
    draw_chip(4.0, 43.5, 3.5, 3.0, "SW1", "RESET", color='#8b949e')
    draw_chip(4.0, 38.5, 3.5, 3.0, "SW2", "BOOT", color='#8b949e')

    # LED1, LED2, LED3: (7, 10, 13, 35)
    ax.add_patch(Circle((7.0, 35.0), 0.9, facecolor='#f85149', edgecolor='#fff', linewidth=0.5, zorder=7))
    ax.add_patch(Circle((10.0, 35.0), 0.9, facecolor='#58a6ff', edgecolor='#fff', linewidth=0.5, zorder=7))
    ax.add_patch(Circle((13.0, 35.0), 0.9, facecolor='#2ea043', edgecolor='#fff', linewidth=0.5, zorder=7))
    ax.text(10.0, 33.0, "[LED1: Alarm | LED2: BLE | LED3: LTE]", color='#8b949e', fontsize=5.0, ha='center', zorder=7)

    # U6: İdeal Diyot (62, 30), U5: Şarj (72, 30), J3: Bat (81, 24)
    draw_chip(62.0, 30.0, 3.0, 3.0, "U6", "LM66100", color='#3fb950')
    draw_chip(72.0, 30.0, 5.0, 4.0, "U5: Şarj", "CN3058 (3.65V)", color='#3fb950')
    draw_chip(81.0, 24.0, 6.0, 5.0, "J3: Bat", "JST-PH 2P", color='#3fb950')

    # CAN Grubu: D2 ESD (16, 20) ve U8 CAN (12, 25) - Daisy-chain sırası
    draw_chip(16.0, 20.0, 3.0, 2.5, "D2", "PESD2CAN", color='#d29922')
    draw_chip(12.0, 25.0, 5.0, 4.0, "U8: CAN", "SN65HVD230", color='#d29922')

    # U3: IMU (40.0, 34.0) - Röle şokundan uzak, sessiz merkeze taşındı!
    draw_chip(40.0, 34.0, 3.5, 3.5, "U3: IMU", "LIS3DH (Sessiz Zon)", color='#3fb950', bg='#238636')

    # C4: Tantal (58, 22)
    draw_chip(58.0, 22.0, 7.3, 4.3, "C4: Tantal", "100uF GSM", color='#d29922')

    # Antenler: ANT1 (75, 10 - H2'den uzak), ANT2 (75, 18)
    ax.add_patch(Circle((75.0, 10.0), 1.5, facecolor='#d29922', edgecolor='#fff', linewidth=0.6, zorder=7))
    ax.add_patch(Circle((75.0, 18.0), 1.5, facecolor='#d29922', edgecolor='#fff', linewidth=0.6, zorder=7))
    ax.text(78.5, 10.0, "ANT1 (LTE)", color='#d29922', fontsize=5.8, fontweight='bold', va='center', zorder=8)
    ax.text(78.5, 18.0, "ANT2 (GPS)", color='#d29922', fontsize=5.8, fontweight='bold', va='center', zorder=8)

    # Röleler ve Sürücüler + Flyback Diyotları (D4, D5, D6)
    draw_chip(14.0, 14.0, 12.0, 12.0, "K1: Kontak", "30A Omron G8HN", color='#ec6547', bg='#2d1f1f')
    draw_chip(10.0, 12.0, 2.5, 1.8, "D4", "Flyback", color='#ec6547')  # K1 Flyback
    draw_chip(9.0, 20.0, 3.0, 2.5, "Q4", "K1 Drv", color='#ec6547')

    draw_chip(25.0, 14.0, 10.0, 7.5, "K2: Marş", "TX2-12V SMD", color='#ec6547', bg='#2d1f1f')
    draw_chip(21.0, 12.0, 2.5, 1.8, "D5", "Flyback", color='#ec6547')  # K2 Flyback
    draw_chip(21.0, 20.0, 3.0, 2.5, "Q2", "K2 Drv", color='#ec6547')

    draw_chip(34.0, 14.0, 10.0, 7.5, "K3: Kill", "TX2-12V SMD", color='#ec6547', bg='#2d1f1f')
    draw_chip(30.0, 12.0, 2.5, 1.8, "D6", "Flyback", color='#ec6547')  # K3 Flyback
    draw_chip(30.0, 20.0, 3.0, 2.5, "Q3", "K3 Drv", color='#ec6547')

    draw_chip(38.0, 20.0, 3.0, 2.5, "Q5", "Siren Drv", color='#ec6547')

    # U9: İzo Opto (42, 10)
    draw_chip(42.0, 10.0, 5.0, 4.0, "U9: İzo", "LTV-356T", color='#3fb950')

    # U2: SIM7080G (62, 14)
    draw_chip(62.0, 14.0, 17.6, 15.7, "U2: SIM7080G", "LTE-M / GNSS (62,14)", color='#f85149', bg='#2c1f24')
    ax.add_patch(Rectangle((54.0, 7.0), 16.0, 14.0, facecolor='#30363d', edgecolor='#8b949e', linewidth=0.6, zorder=6))
    ax.text(62.0, 14.0, "SIMCom\nSIM7080G", color='#f85149', fontsize=6.2, fontweight='bold', ha='center', va='center', zorder=8)

    # J2: SIM Alt Yüzey (62, 14 - Kesikli)
    sim_slot = Rectangle((55.0, 8.0), 14.0, 12.0, facecolor='none', edgecolor='#8b949e', linestyle=':', linewidth=1.0, zorder=6)
    ax.add_patch(sim_slot)
    ax.text(62.0, 3.5, "[J2: Nano SIM - Alt Yüzey (B.Cu)]", color='#8b949e', fontsize=5.2, ha='center', zorder=7)

    # J1: Molex 14-Pin (28, 3.5)
    draw_chip(28.0, 3.5, 24.0, 5.5, "J1: Molex Micro-Fit 14P (Alt Kenar)", "Ana Tesisat Soketi (43045-1400)", color='#f0883e', bg='#30363d')

    # 5. CAD Ölçülendirme Çizgileri
    y_dim_top = 62.0
    ax.annotate('', xy=(0, y_dim_top), xytext=(85.0, y_dim_top), arrowprops=dict(arrowstyle='<->', color='#58a6ff', lw=1.2))
    ax.plot([0, 0], [55, y_dim_top+2], color='#58a6ff', lw=0.6, linestyle=':')
    ax.plot([85, 85], [55, y_dim_top+2], color='#58a6ff', lw=0.6, linestyle=':')
    ax.text(42.5, y_dim_top + 1.5, "85.00 mm (Genişlik)", color='#58a6ff', fontsize=9, fontweight='bold', ha='center')

    x_dim_right = 93.0
    ax.annotate('', xy=(x_dim_right, 0), xytext=(x_dim_right, 55.0), arrowprops=dict(arrowstyle='<->', color='#58a6ff', lw=1.2))
    ax.plot([85, x_dim_right+2], [0, 0], color='#58a6ff', lw=0.6, linestyle=':')
    ax.plot([85, x_dim_right+2], [55, 55], color='#58a6ff', lw=0.6, linestyle=':')
    ax.text(x_dim_right + 1.5, 27.5, "55.00 mm\n(Yükseklik)", color='#58a6ff', fontsize=9, fontweight='bold', va='center')

    # Başlık
    ax.text(0, 69.0, "AutoMoto — Denetim Sonrası Revize Edilmiş 1:1 CAD Floorplan", color='#ffffff', fontsize=12, fontweight='bold')
    ax.text(0, 66.5, "EMC & Transient Loop Minimize Edildi | M3 Vida Çakışmaları Giderildi | Flyback Korumalı", color='#8b949e', fontsize=8)

    plt.tight_layout()
    png_path = os.path.join(OUTPUT_DIR, "pcb_mechanical_floorplan.png")
    svg_path = os.path.join(OUTPUT_DIR, "pcb_mechanical_floorplan.svg")
    plt.savefig(png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.savefig(svg_path, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Generated 2D CAD: {png_path} and {svg_path}")

if __name__ == "__main__":
    generate_floorplan()
