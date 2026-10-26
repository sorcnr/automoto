#include "failsafe.h"
#include "board_pins.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"

static const char *TAG = "FAILSAFE";
static volatile soft_kill_state_t current_kill_state = KILL_STATE_IDLE;
static TaskHandle_t soft_kill_task_handle = NULL;

static void soft_kill_worker_task(void *pvParameters)
{
    ESP_LOGW(TAG, "EMERGENCY: Soft-Kill procedure initiated!");

    // Aşama 1: Tork Düşürme (Ateşleme Hattı 15ms aralıklarla kesilip verilir)
    current_kill_state = KILL_STATE_PULSING_TORQUE_CUT;
    ESP_LOGW(TAG, "Stage 1: Pulsing ignition line to gently reduce speed...");
    for (int i = 0; i < 100; i++) { // ~3 saniye boyunca puls uygula
        board_set_kill_ssr(true);
        vTaskDelay(pdMS_TO_TICKS(15));
        board_set_kill_ssr(false);
        vTaskDelay(pdMS_TO_TICKS(15));
    }

    // Aşama 2: Akustik ve Görsel Baskı
    current_kill_state = KILL_STATE_ACOUSTIC_WARNING;
    ESP_LOGW(TAG, "Stage 2: Sounding 110 dB siren and flashing hazards...");
    board_set_siren(true);
    vTaskDelay(pdMS_TO_TICKS(2000)); // 2 saniye sesli ikaz

    // Aşama 3: Araç durduğunda kontak kalıcı kesilir
    current_kill_state = KILL_STATE_FULL_LOCKOUT;
    ESP_LOGE(TAG, "Stage 3: Full lockout! Opening PROFET main ignition switch.");
    board_set_ignition(false);
    board_set_kill_ssr(true); // Ateşlemeyi kalıcı toprağa çek

    // Siren alarmını aralıklı çalmaya devam et
    while (current_kill_state == KILL_STATE_FULL_LOCKOUT) {
        board_set_siren(true);
        vTaskDelay(pdMS_TO_TICKS(500));
        board_set_siren(false);
        vTaskDelay(pdMS_TO_TICKS(500));
    }

    vTaskDelete(NULL);
}

esp_err_t failsafe_init(void)
{
    current_kill_state = KILL_STATE_IDLE;
    return ESP_OK;
}

void failsafe_trigger_soft_kill(void)
{
    if (soft_kill_task_handle == NULL) {
        xTaskCreatePinnedToCore(
            soft_kill_worker_task,
            "soft_kill_task",
            4096,
            NULL,
            configMAX_PRIORITIES - 1, // En yüksek öncelik
            &soft_kill_task_handle,
            0 // Core 0
        );
    }
}

void failsafe_cancel_soft_kill(void)
{
    if (soft_kill_task_handle != NULL) {
        vTaskDelete(soft_kill_task_handle);
        soft_kill_task_handle = NULL;
    }
    board_set_siren(false);
    board_set_kill_ssr(false);
    current_kill_state = KILL_STATE_IDLE;
    ESP_LOGI(TAG, "Soft-Kill aborted. System returned to normal.");
}

soft_kill_state_t failsafe_get_kill_state(void)
{
    return current_kill_state;
}

bool failsafe_can_crank_starter(void)
{
    if (current_kill_state != KILL_STATE_IDLE) {
        return false;
    }
    return board_is_neutral();
}
