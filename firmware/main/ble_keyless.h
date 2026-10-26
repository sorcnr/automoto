#ifndef BLE_KEYLESS_H
#define BLE_KEYLESS_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define BLE_MAX_ALLOWED_RTT_US   18000 // 18 ms maksimum gecikme eşiği (Anti-Relay Koruması)
#define BLE_AUTH_NONCE_SIZE     16    // 16 Bayt Rastgele Soru (Challenge)

typedef struct {
    uint8_t nonce[BLE_AUTH_NONCE_SIZE];
    int64_t sent_timestamp_us;
    bool is_pending;
} ble_challenge_ctx_t;

esp_err_t ble_keyless_init(void);
void ble_keyless_start_scan(void);
bool ble_keyless_verify_challenge_response(const uint8_t *response, size_t len, int64_t received_timestamp_us);

#ifdef __cplusplus
}
#endif

#endif // BLE_KEYLESS_H
