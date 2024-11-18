from machine import Pin
import time
from node import UWBNode
from tag import UWBTag
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x0420 #update for src



async def main():

    # Create receiver instance
    tag = UWBTag(PAN_ID, SRC_ADDR)
    
    # Initialize
    await tag.init()
    
    '''# Start continuous ranging
    def distance_callback(distance):
        print(f"Distance: {distance:.3f} m ({distance/.0254:.2f} in)")
    
    await receiver.start_continuous_ranging(callback=distance_callback)'''

    await tag.start_handshake()

uasyncio.run(main())