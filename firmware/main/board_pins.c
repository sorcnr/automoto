#include "board_pins.h"
#include "esp_log.h"

static const char *TAG = "BOARD_PINS";

esp_err_t board_pins_init(void)
{
    ESP_LOGI(TAG, "Initializing AutoMoto GPIO hardware lines...");

    // 1. Çıkış Pinlerini Yapılandır (Röleler, LED'ler, Siren, Modem Kontrol)
    // Varsayılan Güvenli Durum: Tüm röleler ve siren pasif (LOW) başlar
    uint64_t output_pin_mask = 
        (1ULL << PIN_SSR_KILL)    |
        (1ULL << PIN_PROFET_IN)   |
        (1ULL << PIN_SSR_STARTER) |
        (1ULL << PIN_PROFET_DEN)  |
        (1ULL << PIN_SIREN_CTRL)  |
        (1ULL << PIN_MODEM_PWRKEY)|
        (1ULL << PIN_LED_GSM)     |
        (1ULL << PIN_LED_ALARM)   |
        (1ULL << PIN_LED_BLE);

    gpio_config_t out_conf = {
        .pin_bit_mask = output_pin_mask,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&out_conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure output GPIOs: %s", esp_err_to_name(err));
        return err;
    }

    // İlk donanımsal güvenlik reset seviyeleri
    gpio_set_level(PIN_SSR_KILL, 0);
    gpio_set_level(PIN_PROFET_IN, 0);
    gpio_set_level(PIN_SSR_STARTER, 0);
    gpio_set_level(PIN_PROFET_DEN, 0);
    gpio_set_level(PIN_SIREN_CTRL, 0);
    gpio_set_level(PIN_MODEM_PWRKEY, 0);
    gpio_set_level(PIN_LED_GSM, 0);
    gpio_set_level(PIN_LED_ALARM, 0);
    gpio_set_level(PIN_LED_BLE, 0);

    // 2. Giriş Pinlerini Yapılandır (Boş Vites, Modem Durumu, Sensör Kesmeleri)
    gpio_config_t in_conf = {
        .pin_bit_mask = (1ULL << PIN_SENSE_NEUTRAL) | (1ULL << PIN_MODEM_STATUS),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE, // Boş vites optokuplörü için dahili pull-up
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&in_conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure input GPIOs: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "All GPIOs safely configured in fail-safe default states.");
    return ESP_OK;
}

void board_set_ignition(bool state)
{
    gpio_set_level(PIN_PROFET_IN, state ? 1 : 0);
    gpio_set_level(PIN_PROFET_DEN, state ? 1 : 0); // Teşhis hattını da aç
    ESP_LOGI(TAG, "Ignition PROFET state: %s", state ? "ON (Closed)" : "OFF (Open)");
}

void board_set_starter(bool state)
{
    // Donanımsal/Mantıksal Güvenlik: Asla vites boşa alınmadan marş basılamaz!
    if (state && !board_is_neutral()) {
        ESP_LOGW(TAG, "CRITICAL: Starter blocked! Bike is in GEAR!");
        gpio_set_level(PIN_SSR_STARTER, 0);
        return;
    }
    gpio_set_level(PIN_SSR_STARTER, state ? 1 : 0);
}

void board_set_siren(bool state)
{
    gpio_set_level(PIN_SIREN_CTRL, state ? 1 : 0);
}

void board_set_kill_ssr(bool state)
{
    gpio_set_level(PIN_SSR_KILL, state ? 1 : 0);
}

bool board_is_neutral(void)
{
    // LTV-356T optokuplör şaseye çeker (Active LOW)
    return gpio_get_level(PIN_SENSE_NEUTRAL) == 0;
}
