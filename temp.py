from machine import Pin
import time
from receive import UWBNode
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234 #update for src



async def main():

    # Create receiver instance
    receiver = UWBNode(PAN_ID, SRC_ADDR)
    
    # Initialize
    await receiver.init()
    
    '''# Start continuous ranging
    def distance_callback(distance):
        print(f"Distance: {distance:.3f} m ({distance/.0254:.2f} in)")
    
    await receiver.start_continuous_ranging(callback=distance_callback)'''

    await receiver.start_handshake()

uasyncio.run(main())