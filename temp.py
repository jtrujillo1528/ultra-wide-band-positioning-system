from machine import Pin
import time
from receive import init, twr_response, get_calibration_data, get_distance
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234 #update for src

#ble = BLEHandler(f"PicoW-{SRC_ADDR}")

async def main():
    await init(PAN_ID, SRC_ADDR)
    print("searching")
    while True:
        # Perform TWR and transmit our own message
        isResponse = await twr_response()
        if isResponse == True:
            d = await get_distance()
            print(f"distance (in): {d/.0254}")
        
        await uasyncio.sleep_ms(50)

uasyncio.run(main())