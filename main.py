from machine import Pin
import time
from transmit import init, twr_transmit
from ble_handler import BLEHandler, create_ble_message
from random import randint
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x5678 #update for src

ble = BLEHandler(f"PicoW-{SRC_ADDR}")

async def main():
    await init(PAN_ID, SRC_ADDR)
    while True:
        num = randint(0,255)
        result = await twr_transmit(PAN_ID, SRC_ADDR, 0x1234, num)
        print(result)
        if result == False:
            await init(PAN_ID, 0x1234)
        # Scan for and process other BLE messages
        ble.scan_and_process()
        await uasyncio.sleep(1)

uasyncio.run(main())