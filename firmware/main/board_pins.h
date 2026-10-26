#ifndef BOARD_PINS_H
#define BOARD_PINS_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/gpio.h"
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

// ==============================================================================
// AutoMoto ESP32-S3-WROOM-1U Pin Eşleşmeleri (PCB v4.0 Spesifikasyonu)
// ==============================================================================

// I2C Veri Yolu (LIS3DH MEMS İvmeölçer)
#define PIN_I2C_SDA             GPIO_NUM_1
#define PIN_I2C_SCL             GPIO_NUM_2

// Katı-Hal Röleler ve Güç Anahtarları
#define PIN_SSR_KILL            GPIO_NUM_3   // U12: VO14642AAB Motor Ateşleme Kesici (Active HIGH)
#define PIN_PROFET_IN           GPIO_NUM_8   // U10: BTS7002-1EPP 25A Kontak Anahtarı (Active HIGH)
#define PIN_SSR_STARTER         GPIO_NUM_9   // U11: VO14642AAB Marş SSR (Active HIGH)
#define PIN_PROFET_DEN          GPIO_NUM_15  // U10: Teşhis Yetkilendirme (Diagnostic Enable)
#define PIN_PROFET_IS           GPIO_NUM_10  // U10: IS Akım Ölçüm Şöntü (ADC1_CHANNEL_9)

// Ses ve Emniyet Giriş/Çıkışları
#define PIN_SIREN_CTRL          GPIO_NUM_11  // Q5: DMN6075S N-FET 110 dB Siren Sürücüsü (Active HIGH)
#define PIN_SENSE_NEUTRAL       GPIO_NUM_12  // U9: LTV-356T Boş Vites Algılama (Active LOW)

// MEMS Sensör Kesme Hatları (LIS3DH)
#define PIN_IMU_INT1            GPIO_NUM_4   // Sarsıntı / Uyandırma Kesmesi
#define PIN_IMU_INT2            GPIO_NUM_5   // Kaza / Devrilme Algılama Kesmesi

// CAN-Bus (SN65HVD230 Alıcı-Verici)
#define PIN_CAN_TX              GPIO_NUM_6
#define PIN_CAN_RX              GPIO_NUM_7

// Hücresel Modem Arayüzü (SIM808 / Quectel EG915U UART & Kontrol)
#define PIN_MODEM_TX            GPIO_NUM_17  // ESP TX -> Modem RXD
#define PIN_MODEM_RX            GPIO_NUM_18  // ESP RX <- Modem TXD
#define PIN_MODEM_STATUS        GPIO_NUM_21  // Modem Açık Durum Girişi
#define PIN_MODEM_PWRKEY        GPIO_NUM_38  // Modem Açma/Kapama Pals Çıkışı

// Kullanıcı Bildirim LED'leri (Active HIGH)
#define PIN_LED_GSM             GPIO_NUM_46  // LED3 (Yeşil): GSM / Şebeke Durumu
#define PIN_LED_ALARM           GPIO_NUM_47  // LED1 (Kırmızı): Alarm / Sabotaj Durumu
#define PIN_LED_BLE             GPIO_NUM_48  // LED2 (Mavi): Keyless BLE Durumu

// Fonksiyon Prototipleri
esp_err_t board_pins_init(void);
void board_set_ignition(bool state);
void board_set_starter(bool state);
void board_set_siren(bool state);
void board_set_kill_ssr(bool state);
bool board_is_neutral(void);

#ifdef __cplusplus
}
#endif

#endif // BOARD_PINS_H
