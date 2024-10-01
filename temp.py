from machine import Pin
import time
from receive import init, twr_response, get_distance, get_calibration_data
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234 #update for src

async def main():
    
    await init(PAN_ID, SRC_ADDR)
    print("searching")
    while True:
        isResponse = await twr_response()
        if isResponse == True:
            t1, t2 = await get_calibration_data()
            print(f"t1: {t1}")
            print(f"t2: {t2}")
        await uasyncio.sleep_ms(50)

uasyncio.run(main())