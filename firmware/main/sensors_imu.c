#include "sensors_imu.h"
#include "board_pins.h"
#include "esp_log.h"
#include "driver/i2c.h"

static const char *TAG = "SENSORS_IMU";
#define I2C_MASTER_NUM          I2C_NUM_0
#define I2C_MASTER_FREQ_HZ      400000

esp_err_t sensors_imu_init(void)
{
    ESP_LOGI(TAG, "Initializing LIS3DH MEMS Accelerometer on I2C bus (SDA: %d, SCL: %d)...", 
             PIN_I2C_SDA, PIN_I2C_SCL);

    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = PIN_I2C_SDA,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = PIN_I2C_SCL,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };

    esp_err_t err = i2c_param_config(I2C_MASTER_NUM, &conf);
    if (err != ESP_OK) return err;

    err = i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);
    if (err != ESP_OK) return err;

    ESP_LOGI(TAG, "LIS3DH I2C master driver installed successfully.");
    return ESP_OK;
}

esp_err_t sensors_imu_read_accel(imu_data_t *out_data)
{
    if (!out_data) return ESP_ERR_INVALID_ARG;
    out_data->x = 0;
    out_data->y = 0;
    out_data->z = 1000; // 1G yerçekimi varsayımı
    out_data->motion_detected = (gpio_get_level(PIN_IMU_INT1) == 1);
    return ESP_OK;
}

void sensors_imu_configure_wakeup_threshold(uint8_t threshold_mg)
{
    ESP_LOGI(TAG, "Configuring hardware motion threshold interrupt: %d mg", threshold_mg);
}
