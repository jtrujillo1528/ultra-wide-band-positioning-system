from machine import Pin
import time
from receive import UWBReceiver
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234 #update for src


async def main():
    # Example parameters
    PAN_ID = 0xB34A
    SRC_ADDR = 0x1234  # For receiver

    # Create receiver instance
    receiver = UWBReceiver()
    
    # Initialize
    await receiver.init(PAN_ID, SRC_ADDR)
    
    # Start continuous ranging
    def distance_callback(distance):
        print(f"Distance: {distance:.3f} m ({distance/.0254:.2f} in)")
    
    await receiver.start_continuous_ranging(callback=distance_callback)

uasyncio.run(main())