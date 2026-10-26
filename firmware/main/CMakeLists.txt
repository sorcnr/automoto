# AutoMoto Firmware — Main Component CMakeLists
idf_component_register(
    SRCS 
        "main.c"
        "board_pins.c"
        "actuator_safety.c"
        "failsafe.c"
        "power_manager.c"
        "ble_keyless.c"
        "sensors_imu.c"
        "modem.c"
    INCLUDE_DIRS "."
    REQUIRES 
        nvs_flash 
        esp_timer 
        driver 
        freertos 
        bt 
        esp_pm 
        mbedtls 
        esp_partition 
        esp_event
        app_update
        esp_system
        log
)
