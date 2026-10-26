#include "modem.h"
#include "board_pins.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>

static const char *TAG = "MODEM_HAL";
#define MODEM_UART_PORT         UART_NUM_1
#define MODEM_BAUD_RATE         115200
#define MODEM_BUF_SIZE          1024

static modem_hardware_type_t current_modem_type = MODEM_TYPE_SIM808;

esp_err_t modem_init(modem_hardware_type_t type)
{
    current_modem_type = type;
    ESP_LOGI(TAG, "Initializing Cellular Modem HAL (%s) on UART1 (TX: %d, RX: %d)...",
             (type == MODEM_TYPE_SIM808) ? "SIMCom SIM808" : "Quectel EG915U-EU",
             PIN_MODEM_TX, PIN_MODEM_RX);

    uart_config_t uart_config = {
        .baud_rate = MODEM_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    esp_err_t err = uart_param_config(MODEM_UART_PORT, &uart_config);
    if (err != ESP_OK) return err;

    err = uart_set_pin(MODEM_UART_PORT, PIN_MODEM_TX, PIN_MODEM_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (err != ESP_OK) return err;

    err = uart_driver_install(MODEM_UART_PORT, MODEM_BUF_SIZE * 2, 0, 0, NULL, 0);
    if (err != ESP_OK) return err;

    ESP_LOGI(TAG, "Modem UART driver installed. Verifying power state...");
    if (!modem_is_alive()) {
        modem_power_cycle();
    }
    return ESP_OK;
}

esp_err_t modem_power_cycle(void)
{
    ESP_LOGI(TAG, "Pulsing MODEM_PWRKEY (GPIO %d) for 1.2s to toggle power...", PIN_MODEM_PWRKEY);
    gpio_set_level(PIN_MODEM_PWRKEY, 1);
    vTaskDelay(pdMS_TO_TICKS(1200));
    gpio_set_level(PIN_MODEM_PWRKEY, 0);
    vTaskDelay(pdMS_TO_TICKS(2000)); // Başlatma için bekle
    return ESP_OK;
}

bool modem_is_alive(void)
{
    return gpio_get_level(PIN_MODEM_STATUS) == 1;
}

esp_err_t modem_send_at(const char *command, char *response_out, size_t max_len, uint32_t timeout_ms)
{
    if (!command) return ESP_ERR_INVALID_ARG;
    
    uart_flush(MODEM_UART_PORT);
    uart_write_bytes(MODEM_UART_PORT, command, strlen(command));
    uart_write_bytes(MODEM_UART_PORT, "\r\n", 2);

    if (response_out && max_len > 0) {
        int len = uart_read_bytes(MODEM_UART_PORT, (uint8_t *)response_out, max_len - 1, pdMS_TO_TICKS(timeout_ms));
        if (len > 0) {
            response_out[len] = '\0';
            return ESP_OK;
        }
        return ESP_ERR_TIMEOUT;
    }
    return ESP_OK;
}

esp_err_t modem_get_gnss_fix(gnss_telemetry_t *fix)
{
    if (!fix) return ESP_ERR_INVALID_ARG;
    // Varsayılan mock koordinatları (İzmir / Test)
    fix->latitude = 38.4237;
    fix->longitude = 27.1428;
    fix->speed_kmh = 0.0f;
    fix->satellites = 9;
    fix->gps_fixed = true;
    return ESP_OK;
}
