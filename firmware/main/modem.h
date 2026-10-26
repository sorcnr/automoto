#ifndef MODEM_H
#define MODEM_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    MODEM_TYPE_SIM808 = 0,      // Prototip v4.0 (2G GSM + GPS)
    MODEM_TYPE_QUECTEL_EG915U   // Seri Üretim (LTE Cat-1 bis + GNSS)
} modem_hardware_type_t;

typedef struct {
    double latitude;
    double longitude;
    float speed_kmh;
    uint8_t satellites;
    bool gps_fixed;
} gnss_telemetry_t;

esp_err_t modem_init(modem_hardware_type_t type);
esp_err_t modem_power_cycle(void);
bool modem_is_alive(void);
esp_err_t modem_send_at(const char *command, char *response_out, size_t max_len, uint32_t timeout_ms);
esp_err_t modem_get_gnss_fix(gnss_telemetry_t *fix);

#ifdef __cplusplus
}
#endif

#endif // MODEM_H
