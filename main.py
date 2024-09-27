from machine import Pin
import time
from transmit import init, twr_transmit
from random import randint

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x5678 #update for src

if __name__ == "__main__":
    init(PAN_ID, 0x1234)
    while True:
        num = randint(0,255)
        result = twr_transmit(PAN_ID, SRC_ADDR, 0x1234, num)
        print(result)
        if result == False:
            init(PAN_ID, 0x1234)
        time.sleep(2)