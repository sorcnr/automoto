#ifndef FAILSAFE_H
#define FAILSAFE_H

#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    KILL_STATE_IDLE = 0,
    KILL_STATE_PULSING_TORQUE_CUT, // Aşama 1: 15ms SSR puls ile tork düşürme (<20 km/h)
    KILL_STATE_ACOUSTIC_WARNING,   // Aşama 2: Siren ve flaşör ikazı
    KILL_STATE_FULL_LOCKOUT        // Aşama 3: Araç durduğunda (V=0) tam kontak kilit
} soft_kill_state_t;

esp_err_t failsafe_init(void);
void failsafe_trigger_soft_kill(void);
void failsafe_cancel_soft_kill(void);
soft_kill_state_t failsafe_get_kill_state(void);
bool failsafe_can_crank_starter(void);

#ifdef __cplusplus
}
#endif

#endif // FAILSAFE_H
