#include <stdio.h>
#include <string.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_ota_ops.h"
#include "esp_task_wdt.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "board_pins.h"
#include "actuator_safety.h"
#include "failsafe.h"
#include "power_manager.h"
#include "ble_keyless.h"
#include "sensors_imu.h"
#include "modem.h"

static const char *TAG = "MAIN";

// Core 0: Güvenlik, BLE Keyless, Sensör Kesmeleri ve Soft-Kill
static void safety_core0_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Starting Safety & Keyless Task on Core 0...");
    imu_data_t imu_data;

    while (1) {
        // 1. IMU Hareket / Sarsıntı Denetimi
        sensors_imu_read_accel(&imu_data);
        if (imu_data.motion_detected) {
            ESP_LOGW(TAG, "Movement detected! Verifying vehicle authorization...");
            gpio_set_level(PIN_LED_ALARM, 1);
        } else {
            gpio_set_level(PIN_LED_ALARM, 0);
        }

        // 2. BLE Keyless Tarama / Doğrulama
        ble_keyless_start_scan();

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

// Core 1: Hücresel Haberleşme (GSM/LTE), GNSS ve MQTT Telemetri
static void cellular_core1_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Starting Cellular & Telemetry Task on Core 1...");
    gnss_telemetry_t gnss_fix;

    while (1) {
        // 1. Hücresel Şebeke ve Modem Durumu
        if (modem_is_alive()) {
            gpio_set_level(PIN_LED_GSM, 1);
        } else {
            gpio_set_level(PIN_LED_GSM, 0);
            modem_power_cycle();
        }

        // 2. GNSS Konum Okuma
        modem_get_gnss_fix(&gnss_fix);
        ESP_LOGI(TAG, "Telemetry Tick: Bike Lat: %.4f, Lng: %.4f, Neutral: %s, Ignition: %s, Cranking: %s",
                 gnss_fix.latitude, gnss_fix.longitude,
                 board_is_neutral() ? "YES (Safe)" : "IN GEAR",
                 actuator_is_ignition_on() ? "ON" : "OFF",
                 actuator_is_cranking() ? "YES" : "NO");

        vTaskDelay(pdMS_TO_TICKS(3000));
    }
}

static void verify_and_confirm_ota_rollback(void)
{
    const esp_partition_t *running = esp_ota_get_running_partition();
    esp_ota_img_states_t ota_state;
    if (esp_ota_get_state_partition(running, &ota_state) == ESP_OK) {
        if (ota_state == ESP_OTA_IMG_PENDING_VERIFY) {
            ESP_LOGW(TAG, "==========================================================");
            ESP_LOGW(TAG, "  OTA UPDATE CONFIRMATION:");
            ESP_LOGW(TAG, "  New firmware booted successfully! Self-checks passed.");
            ESP_LOGW(TAG, "  Canceling rollback and marking partition '%s' as VALID.", running->label);
            ESP_LOGW(TAG, "==========================================================");
            esp_ota_mark_app_valid_cancel_rollback();
        } else {
            ESP_LOGI(TAG, "Firmware partition '%s' is in verified valid state.", running->label);
        }
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "==========================================================");
    ESP_LOGI(TAG, "  AutoMoto Smart Security & Telemetry Platform v4.0");
    ESP_LOGI(TAG, "  MCU: ESP32-S3 (Dual-Core 240MHz, 16MB Flash, NimBLE BLE)");
    ESP_LOGI(TAG, "  Safety: Watchdog Protected Actuators & Secure OTA Rollback");
    ESP_LOGI(TAG, "==========================================================");

    // 1. NVS Flash Başlatma (Güvenlik anahtarları ve WiFi/BLE eşleşmeleri için)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 2. Donanım GPIO ve Röle Emniyet Seviyelerini Kur
    ESP_ERROR_CHECK(board_pins_init());

    // 3. Emniyet ve Fail-Safe Çekirdeğini Kur
    ESP_ERROR_CHECK(failsafe_init());

    // 4. Donanımsal Watchdog ve Aktüatör Güvenlik Görevini Başlat (Core 0, Max Priority)
    ESP_ERROR_CHECK(actuator_safety_init());

    // 5. Güç Yönetimini Başlat ve Uyanma Nedenini Oku
    ESP_ERROR_CHECK(power_manager_init());
    automoto_wakeup_reason_t wakeup = power_manager_get_wakeup_cause();
    ESP_LOGI(TAG, "Wakeup Cause ID: %d", wakeup);

    // 6. MEMS İvmeölçer (LIS3DH) Başlat
    ESP_ERROR_CHECK(sensors_imu_init());

    // 7. NimBLE Keyless Go Başlat
    ESP_ERROR_CHECK(ble_keyless_init());

    // 8. Hücresel Modem (SIM808 / EG915U) Başlat
    ESP_ERROR_CHECK(modem_init(MODEM_TYPE_SIM808));

    // 9. OTA Güncelleme Başarı Teyidi (Self-Test Başarılı ise Rollback'i İptal Et)
    verify_and_confirm_ota_rollback();

    // 10. Çift Çekirdekli FreeRTOS Görevlerini Başlat
    xTaskCreatePinnedToCore(safety_core0_task, "safety_core0", 4096, NULL, 5, NULL, 0);
    xTaskCreatePinnedToCore(cellular_core1_task, "cellular_core1", 4096, NULL, 4, NULL, 1);

    ESP_LOGI(TAG, "AutoMoto system initialized successfully in secure state.");
}
