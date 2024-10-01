# main.py
from machine import Pin
import time
from receive import init, twr_response, get_calibration_data
from ble_handler import BLEHandler, create_ble_message
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234 #update for src

ble = BLEHandler(f"PicoW-{SRC_ADDR}")
message_counter = 0

async def main():
    global message_counter
    
    await init(PAN_ID, SRC_ADDR)
    print("searching")
    while True:
        isResponse = await twr_response()
        if isResponse == True:
            t1, t2 = await get_calibration_data()
            print(f"t1: {t1}")
            print(f"t2: {t2}")
            
            # Create and send BLE message
            message_id = f"{SRC_ADDR}-{message_counter}"
            message_counter += 1
            hop_count = 3  # Set initial hop count
            ble_message = create_ble_message(message_id, hop_count, t1, t2, SRC_ADDR)
            ble.advertise(ble_message)
        
        await uasyncio.sleep_ms(50)

uasyncio.run(main())