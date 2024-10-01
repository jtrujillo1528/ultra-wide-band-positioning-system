from machine import Pin
import time
from receive import init, twr_response, get_distance, get_calibration_data

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234 #update for src

if __name__ == "__main__":

    init(PAN_ID, SRC_ADDR)

    print("searching")
    while True:
        isResponse = twr_response()
        if isResponse == True:
            t1, t2 = get_calibration_data()
            print(f"t1: {t1}")
            print(f"t2: {t2}")
        time.sleep_us(50)
