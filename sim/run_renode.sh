#!/usr/bin/env bash
# ==============================================================================
# AutoMoto v4.0 - Renode Simulation Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESC_FILE="$SCRIPT_DIR/renode/automoto.resc"

echo "=== AutoMoto v4.0 Renode Simülasyonu Başlatılıyor ==="
echo "Konfigürasyon: $RESC_FILE"

# GUI kontrolü
if [ -n "$DISPLAY" ]; then
    echo "[*] Grafik arayüzü (GUI) algılandı, Renode penceresi açılıyor..."
    renode "$RESC_FILE" "$@"
else
    echo "[*] Grafik arayüzü yok (Headless/CLI modu), Renode terminalde çalıştırılıyor..."
    renode --disable-gui -e "include @$RESC_FILE" "$@"
fi
