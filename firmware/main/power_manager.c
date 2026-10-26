#include "power_manager.h"
#include "board_pins.h"
#include "esp_log.h"

static const char *TAG = "POWER_MGR";

esp_err_t power_manager_init(void)
{
    ESP_LOGI(TAG, "Initializing AutoMoto Power Management subsystem...");
    return ESP_OK;
}

automoto_wakeup_reason_t power_manager_get_wakeup_cause(void)
{
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    switch (cause) {
        case ESP_SLEEP_WAKEUP_TIMER:
            ESP_LOGD(TAG, "Wakeup caused by periodic RTC timer (Keyless BLE check).");
            return WAKEUP_REASON_TIMER_BLE_SCAN;
        case ESP_SLEEP_WAKEUP_EXT0:
            ESP_LOGW(TAG, "Wakeup caused by EXT0 (LIS3DH Motion / Tamper detected!).");
            return WAKEUP_REASON_IMU_MOTION;
        case ESP_SLEEP_WAKEUP_EXT1:
            ESP_LOGI(TAG, "Wakeup caused by EXT1 (Modem Ring Indicator / Network event).");
            return WAKEUP_REASON_MODEM_RING;
        default:
            ESP_LOGI(TAG, "Normal startup or power-on reset.");
            return WAKEUP_REASON_UNKNOWN;
    }
}

void power_manager_enter_deep_sleep(uint64_t sleep_time_us)
{
    ESP_LOGI(TAG, "Configuring wakeup sources and entering Ultra-Low-Power Deep Sleep (%llu ms)...", 
             sleep_time_us / 1000);

    // 1. Periyodik BLE Keyless Tarama Zamanlayıcısı
    if (sleep_time_us > 0) {
        esp_sleep_enable_timer_wakeup(sleep_time_us);
    }

    // 2. LIS3DH Hareket Sensörü Donanımsal Kesmesi (EXT0 - High level)
    esp_sleep_enable_ext0_wakeup(PIN_IMU_INT1, 1);

    // 3. Güç tüketimini en aza indirmek için GPIO durumlarını sabitle
    gpio_set_level(PIN_SSR_KILL, 0);
    gpio_set_level(PIN_SSR_STARTER, 0);
    gpio_set_level(PIN_SIREN_CTRL, 0);

    // Derin Uykuyu Başlat
    esp_deep_sleep_start();
}
