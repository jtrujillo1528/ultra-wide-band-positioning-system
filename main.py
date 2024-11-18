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
    
    # Main loop
    while True:
        sequence_num = randint(0, 255)
        #result = await transmitter.twr(DEST_ADDR, sequence_num)
        result = await node.handshake(sequence_num)
        print(result)
        await node.init()
        await uasyncio.sleep(2)

uasyncio.run(main())