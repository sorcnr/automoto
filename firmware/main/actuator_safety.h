#ifndef ACTUATOR_SAFETY_H
#define ACTUATOR_SAFETY_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define MAX_CRANK_HARD_LIMIT_MS    1500  // Marş motoru için mutlak donanımsal süre sınırı (1.5s)
#define ACTUATOR_QUEUE_LENGTH      10    // Komut kuyruğu derinliği

typedef enum {
    ACT_CMD_IGNITION_SET = 0,
    ACT_CMD_CRANK_START,
    ACT_CMD_CRANK_STOP,
    ACT_CMD_SIREN_SET,
    ACT_CMD_KILL_SSR_SET,
    ACT_CMD_EMERGENCY_SHUTDOWN
} actuator_cmd_type_t;

typedef struct {
    actuator_cmd_type_t type;
    union {
        bool state;
        uint16_t duration_ms; // Marş süresi (ms)
    } data;
} actuator_cmd_t;

// Başlatma ve Donanımsal Watchdog (TWDT) Kaydı
esp_err_t actuator_safety_init(void);

// Thread-Safe Non-Blocking Komut Gönderme Fonksiyonları (Core 1 veya Kesmelerden çağrılabilir)
esp_err_t actuator_send_cmd(const actuator_cmd_t *cmd);
esp_err_t actuator_request_ignition(bool state);
esp_err_t actuator_request_crank(uint16_t duration_ms);
esp_err_t actuator_request_emergency_shutdown(void);

// Durum Sorgulama
bool actuator_is_cranking(void);
bool actuator_is_ignition_on(void);

#ifdef __cplusplus
}
#endif

#endif // ACTUATOR_SAFETY_H
