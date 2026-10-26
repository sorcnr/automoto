#include "actuator_safety.h"
#include "board_pins.h"
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

static const char *TAG = "ACTUATOR_SAFETY";

static QueueHandle_t s_actuator_queue = NULL;
static TaskHandle_t s_actuator_task_handle = NULL;

static volatile bool s_ignition_active = false;
static volatile bool s_cranking_active = false;
static uint32_t s_crank_remaining_ms = 0;

static void actuator_safety_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Actuator Safety Task running on Core 0 (Priority: %d)", uxTaskPriorityGet(NULL));

    // 1. Bu görevi Donanımsal Task Watchdog Timer'a (TWDT) kaydet
    esp_err_t wdt_err = esp_task_wdt_add(NULL);
    if (wdt_err != ESP_OK) {
        ESP_LOGW(TAG, "Failed to register task to TWDT: %s", esp_err_to_name(wdt_err));
    }

    const TickType_t tick_delay = pdMS_TO_TICKS(20); // 20 ms deterministik döngü
    actuator_cmd_t cmd;

    while (1) {
        // 2. Watchdog'u düzenli olarak besle (Feed / Pet Watchdog)
        esp_task_wdt_reset();

        // 3. Kuyruktan gelen komutları non-blocking (veya 20ms timeout ile) tüket
        if (xQueueReceive(s_actuator_queue, &cmd, tick_delay) == pdPASS) {
            switch (cmd.type) {
                case ACT_CMD_IGNITION_SET:
                    s_ignition_active = cmd.data.state;
                    board_set_ignition(s_ignition_active);
                    if (!s_ignition_active && s_cranking_active) {
                        // Kontak kapandıysa marşı da derhal kes
                        s_cranking_active = false;
                        board_set_starter(false);
                    }
                    break;

                case ACT_CMD_CRANK_START:
                    // Güvenlik Kuralı 1: Kontak açık değilse marş basılamaz
                    if (!s_ignition_active) {
                        ESP_LOGW(TAG, "Rejected crank: Ignition is OFF!");
                        break;
                    }
                    // Güvenlik Kuralı 2: Boş vites müşürü doğrulaması
                    if (!board_is_neutral()) {
                        ESP_LOGE(TAG, "SAFETY INTERLOCK: Crank rejected! Motor viteste (Neutral switch is OPEN)!");
                        break;
                    }
                    // Güvenlik Kuralı 3: Süre sınırlaması (Hard-limit denetimi)
                    uint16_t duration = cmd.data.duration_ms;
                    if (duration == 0 || duration > MAX_CRANK_HARD_LIMIT_MS) {
                        duration = MAX_CRANK_HARD_LIMIT_MS;
                    }
                    s_crank_remaining_ms = duration;
                    s_cranking_active = true;
                    board_set_starter(true);
                    ESP_LOGI(TAG, "Starter ENGAGED for %u ms (Hard limit: %d ms)", duration, MAX_CRANK_HARD_LIMIT_MS);
                    break;

                case ACT_CMD_CRANK_STOP:
                    s_cranking_active = false;
                    s_crank_remaining_ms = 0;
                    board_set_starter(false);
                    ESP_LOGI(TAG, "Starter disengaged by command.");
                    break;

                case ACT_CMD_SIREN_SET:
                    board_set_siren(cmd.data.state);
                    break;

                case ACT_CMD_KILL_SSR_SET:
                    board_set_kill_ssr(cmd.data.state);
                    break;

                case ACT_CMD_EMERGENCY_SHUTDOWN:
                    ESP_LOGE(TAG, "EMERGENCY SHUTDOWN TRIGGERED! Forcing all actuators to SAFE OFF.");
                    s_cranking_active = false;
                    s_ignition_active = false;
                    s_crank_remaining_ms = 0;
                    board_set_starter(false);
                    board_set_ignition(false);
                    board_set_kill_ssr(true); // Ateşlemeyi şaseye çek
                    break;
            }
        }

        // 4. Otonom Marş Hard-Limit Zaman Sayacı Denetimi
        if (s_cranking_active) {
            // Sürüş emniyeti: Marş basılırken vitese takılırsa anında kes
            if (!board_is_neutral()) {
                ESP_LOGE(TAG, "SAFETY INTERLOCK TRIPPED DURING CRANK: Neutral lost! Aborting crank immediately!");
                s_cranking_active = false;
                s_crank_remaining_ms = 0;
                board_set_starter(false);
            } else if (s_crank_remaining_ms <= 20) {
                // Zaman aşımı doldu: Harici komut gelmese dahi marşı zorla kes
                s_cranking_active = false;
                s_crank_remaining_ms = 0;
                board_set_starter(false);
                ESP_LOGI(TAG, "Starter AUTO-OFF: Hard-limit duration expired successfully.");
            } else {
                s_crank_remaining_ms -= 20;
            }
        }
    }
}

esp_err_t actuator_safety_init(void)
{
    ESP_LOGI(TAG, "Initializing Actuator Safety Subsystem (Core 0, Watchdog Supervised)...");

    if (s_actuator_queue == NULL) {
        s_actuator_queue = xQueueCreate(ACTUATOR_QUEUE_LENGTH, sizeof(actuator_cmd_t));
        if (s_actuator_queue == NULL) {
            ESP_LOGE(TAG, "Failed to create actuator command queue!");
            return ESP_ERR_NO_MEM;
        }
    }

    if (s_actuator_task_handle == NULL) {
        BaseType_t res = xTaskCreatePinnedToCore(
            actuator_safety_task,
            "actuator_safety",
            4096,
            NULL,
            configMAX_PRIORITIES - 2, // Yüksek güvenlik önceliği
            &s_actuator_task_handle,
            0 // Core 0
        );
        if (res != pdPASS) {
            ESP_LOGE(TAG, "Failed to spawn actuator safety task!");
            return ESP_FAIL;
        }
    }

    return ESP_OK;
}

esp_err_t actuator_send_cmd(const actuator_cmd_t *cmd)
{
    if (!s_actuator_queue || !cmd) return ESP_ERR_INVALID_ARG;
    if (xQueueSend(s_actuator_queue, cmd, pdMS_TO_TICKS(50)) != pdPASS) {
        ESP_LOGE(TAG, "Actuator queue is FULL! Dropped command: %d", cmd->type);
        return ESP_ERR_TIMEOUT;
    }
    return ESP_OK;
}

esp_err_t actuator_request_ignition(bool state)
{
    actuator_cmd_t cmd = {
        .type = ACT_CMD_IGNITION_SET,
        .data.state = state
    };
    return actuator_send_cmd(&cmd);
}

esp_err_t actuator_request_crank(uint16_t duration_ms)
{
    actuator_cmd_t cmd = {
        .type = ACT_CMD_CRANK_START,
        .data.duration_ms = duration_ms
    };
    return actuator_send_cmd(&cmd);
}

esp_err_t actuator_request_emergency_shutdown(void)
{
    actuator_cmd_t cmd = {
        .type = ACT_CMD_EMERGENCY_SHUTDOWN
    };
    return actuator_send_cmd(&cmd);
}

bool actuator_is_cranking(void)
{
    return s_cranking_active;
}

bool actuator_is_ignition_on(void)
{
    return s_ignition_active;
}
