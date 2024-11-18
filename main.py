from node import UWBNode
from random import randint
import uasyncio

'''led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN) ''' # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x5678 #update for src

async def main():
    # Example parameters
    PAN_ID = 0xB34A
    SRC_ADDR = 0x5678
    DEST_ADDR = 0x1234

    # Create transmitter instance
    node = UWBNode(PAN_ID, SRC_ADDR)
    
    # Initialize
    await node.init()

    def distance_callback(distance):
        print(f"Distance: {distance:.3f} m ({distance/.0254:.2f} in)")
    
    # Main loop
    while True:
        result = await node.handshake()
        if result is not None:
            for device in result:
                await node.init()
                await node.start_continuous_ranging(int(device), callback=distance_callback)
        await node.init()
        await uasyncio.sleep(2)

uasyncio.run(main())