#ifndef SENSORS_IMU_H
#define SENSORS_IMU_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define LIS3DH_I2C_ADDR         0x18  // SA0 = GND ise 0x18, VDD ise 0x19

typedef struct {
    int16_t x;
    int16_t y;
    int16_t z;
    bool motion_detected;
} imu_data_t;

esp_err_t sensors_imu_init(void);
esp_err_t sensors_imu_read_accel(imu_data_t *out_data);
void sensors_imu_configure_wakeup_threshold(uint8_t threshold_mg);

#ifdef __cplusplus
}
#endif

#endif // SENSORS_IMU_H
