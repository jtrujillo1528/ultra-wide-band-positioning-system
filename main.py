from machine import Pin
import time
from transmit import UWBTransmitter
from random import randint
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x5678 #update for src

#ble = BLEHandler(f"PicoW-{SRC_ADDR}")

async def main():
    # Example parameters
    PAN_ID = 0xB34A
    SRC_ADDR = 0x5678
    DEST_ADDR = 0x1234

    # Create transmitter instance
    transmitter = UWBTransmitter()
    
    # Initialize
    await transmitter.init(PAN_ID, SRC_ADDR)
    
    # Main loop
    while True:
        sequence_num = randint(0, 255)
        result = await transmitter.twr(PAN_ID, SRC_ADDR, DEST_ADDR, sequence_num)
        print(result)
        if result == False:
            await transmitter.init(PAN_ID, DEST_ADDR)
        await uasyncio.sleep(0.5)

uasyncio.run(main())