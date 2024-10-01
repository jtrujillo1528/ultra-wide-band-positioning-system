import dwmCom
import time
from machine import Pin
import uasyncio

led = Pin("LED", Pin.OUT)  # Onboard LED on the Pico W
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234

SPEED_OF_LIGHT = 299702547 #m/s
UNIT_CONVERSION = 1.565*(10**-11) #s


# Globals for interrupt handling
twr_response_ready = uasyncio.Event()
times_received = uasyncio.Event()
twr_complete = uasyncio.Event()
times_sent = uasyncio.Event()


# Interrupt handlers
def handle_interrupt_times(pin):
    global times_message

    print("times message received")
    times_message = bytearray(dwmCom.read_register_intuitive(0x11,23))
    times_received.set()

def handle_interrupt_tr(pin):
    global r_2, t_3

    twr_response_ready.set()
    r_2 = dwmCom.get_rx_timestamp()
    t_3 = dwmCom.get_tx_timestamp()
    print(r_2)
    print(t_3)
    

def handle_interrupt_twr(pin):
    global tx_time, rx_time
    tx_time = dwmCom.get_tx_timestamp()
    rx_time = dwmCom.get_rx_timestamp()
    twr_complete.set()

async def init(pan_id, src_addr):
    dwmCom.reset()
    dwmCom.setup_radio()
    dwmCom.lde_load()
    dwmCom.init_frame_control(
        pan_id=pan_id,
        device_address=src_addr,
        enable_beacon=True,
        enable_data=True,
        enable_ack=True,
        enable_mac_cmd=False,
        is_coordinator=False,
        enable_reserved=False
    )

async def receive_times(sequence):
    times_received.clear()
    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt_times)
    dwmCom.search()
    try:
        print("wating for times")
        await uasyncio.wait_for(times_received.wait(), 1.0)
    except uasyncio.TimeoutError:
        print("times not received")
        return False
    
    return times_message[20] == sequence



async def twr_response():
    global r_2, t_3, sequence
    dwmCom.init_ack_timing(ack_time=6)
    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    dwmCom.write_register(0x0E,b'\x80\x00\x00\x00')
    
    twr_response_ready.clear()
    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt_tr)
    dwmCom.search()
    try:
        print("searching for message")
        await uasyncio.wait_for(twr_response_ready.wait(), 1.0)
    except uasyncio.TimeoutError:
        print('no message found')
        return False
    
    sequence = dwmCom.read_register_intuitive(0x11,18)[15]
    return await receive_times(sequence)

async def get_distance():
    global t_1, r_2, t_3, r_4, times_message
    r_4 = int(times_message[2:7].hex(),16)
    t_1 = int(times_message[7:12].hex(),16)
    t1 = r_4 - t_1
    t2 = t_3 - r_2
    tof = (t1 - t2)/2
    distance = tof * UNIT_CONVERSION * SPEED_OF_LIGHT
    return distance

async def get_calibration_data():
    global t_1, r_2, t_3, r_4, times_message
    r_4 = int(times_message[2:7].hex(),16)
    t_1 = int(times_message[7:12].hex(),16)
    t1 = r_4 - t_1
    t2 = t_3 - r_2
    return t1, t2

# Main async function
async def main():
    await init(PAN_ID, SRC_ADDR)
    print("searching...")
    while True:
        response = await twr_response()
        if response:
            distance = await get_distance()
            print(f"Distance: {distance} m")
        await uasyncio.sleep(0.05)

# Run the event loop
uasyncio.run(main())
