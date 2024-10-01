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

async def main():
    await init(PAN_ID, SRC_ADDR)
    print("searching")
    while True:
        # Perform TWR and transmit our own message
        isResponse = await twr_response()
        if isResponse == True:
            t1, t2 = await get_calibration_data()
            print(f"t1: {t1}")
            print(f"t2: {t2}")
            
            # Create and send BLE message
            hop_count = 2  # Set initial hop count
            twr_src_addr = 0x5678  # This is the address of the device sending TWR data
            ble_message = create_ble_message(hop_count, t1, t2, SRC_ADDR, twr_src_addr)
            ble.advertise(ble_message)
        
        # Scan for and process other BLE messages
        ble.scan_and_process()
        
        await uasyncio.sleep_ms(50)

uasyncio.run(main())