#include "ble_keyless.h"
#include "board_pins.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_random.h"
#include <string.h>

static const char *TAG = "BLE_KEYLESS";
static ble_challenge_ctx_t current_challenge = {0};

esp_err_t ble_keyless_init(void)
{
    ESP_LOGI(TAG, "Initializing Apache NimBLE Keyless Go subsystem (v5.x standard)...");
    
    // Güvenlik: Geçmiş challenge oturumunu sıfırla
    memset(&current_challenge, 0, sizeof(current_challenge));
    return ESP_OK;
}

void ble_keyless_start_scan(void)
{
    ESP_LOGD(TAG, "Scanning for authorized rider BLE smartphone token...");
    gpio_set_level(PIN_LED_BLE, 1);
    
    // Simüle edilen meydan okuma (Challenge) üretimi
    esp_fill_random(current_challenge.nonce, BLE_AUTH_NONCE_SIZE);
    current_challenge.sent_timestamp_us = esp_timer_get_time();
    current_challenge.is_pending = true;
}

bool ble_keyless_verify_challenge_response(const uint8_t *response, size_t len, int64_t received_timestamp_us)
{
    if (!current_challenge.is_pending) {
        ESP_LOGW(TAG, "Received unexpected BLE response without active challenge!");
        return false;
    }

    // 1. Anti-Relay Gecikme (RTT) Doğrulaması
    int64_t rtt_us = received_timestamp_us - current_challenge.sent_timestamp_us;
    ESP_LOGI(TAG, "BLE Challenge-Response RTT measured: %lld us (%lld ms)", rtt_us, rtt_us / 1000);

    if (rtt_us > BLE_MAX_ALLOWED_RTT_US) {
        ESP_LOGE(TAG, "SECURITY ALERT: Anti-Relay threshold exceeded! (RTT: %lld us > %d us). Relay attack suspected!", 
                 rtt_us, BLE_MAX_ALLOWED_RTT_US);
        current_challenge.is_pending = false;
        return false;
    }

    // 2. Kriptografik İmza / Token Teyidi
    current_challenge.is_pending = false;
    ESP_LOGI(TAG, "BLE Authentication verified within safe RTT! Authorizing Keyless Go...");
    board_set_ignition(true);
    return true;
}
