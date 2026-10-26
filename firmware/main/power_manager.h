#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "esp_sleep.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    WAKEUP_REASON_UNKNOWN = 0,
    WAKEUP_REASON_TIMER_BLE_SCAN,
    WAKEUP_REASON_IMU_MOTION,
    WAKEUP_REASON_MODEM_RING,
    WAKEUP_REASON_POWER_BUTTON
} automoto_wakeup_reason_t;

esp_err_t power_manager_init(void);
automoto_wakeup_reason_t power_manager_get_wakeup_cause(void);
void power_manager_enter_deep_sleep(uint64_t sleep_time_us);

#ifdef __cplusplus
}
#endif

#endif // POWER_MANAGER_H
