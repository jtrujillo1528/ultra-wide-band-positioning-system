import dwmCom
import time
from machine import Pin

led = Pin("LED", Pin.OUT)  # Onboard LED on the Pico W
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234

SPEED_OF_LIGHT = 299702547 #m/s
UNIT_CONVERSION = 1.565*(10**-11) #s

def bytes_to_int(b, byteorder='big'):
    n = 0
    if byteorder == 'big':
        for byte in b:
            n = (n << 8) | byte
    elif byteorder == 'little':
        reversed_result = []
        for i in range(len(b) - 1, -1, -1):
            reversed_result.append(b[i])
        result = reversed_result
        for byte in reversed_result:
            n = (n << 8) | byte
    else:
        raise ValueError("byteorder must be either 'big' or 'little'")
    return n

def init(pan_id, src_addr):
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

def receive_times(sequence):
    global success_times, times_message

    success_times = False

    def handle_interrupt_times(pin):
        global success_times, times_message
        times_message = bytearray(dwmCom.read_register_intuitive(0x11,23))
        
        sequence_received = times_message[20]

        if sequence_received == sequence:
            success_times = True
            led.toggle()

    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt_times)

    count = 0

    while success_times == False and count <= 200:
        last_time = time.ticks_ms()
        dwmCom.search()
        time.sleep_ms(5)
        count += 1

    return success_times



def request_respond():
    global r_2, t_3, success_tr, sequence, times_message

    dwmCom.init_ack_timing(ack_time=6)
    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    #set irq to message send
    dwmCom.write_register(0x0E,b'\x80\x00\x00\x00')

    success_tr = False

    def handle_interrupt_tr(pin):
        global r_2, t_3, success_tr, sequence

        r_2 = dwmCom.get_rx_timestamp()
        t_3 = dwmCom.get_tx_timestamp()

        message = bytearray(dwmCom.read_register_intuitive(0x11,18))
        
        sequence = message[15]

        success_tr = True

        #led.toggle()

    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt_tr)

    count = 0

    while success_tr == False and count <= 200:
        dwmCom.search()
        time.sleep_ms(5)
        count += 1

    if success_tr == True:
        result = receive_times(sequence)
        return result
    
    return False

def get_distance(message):
    global t_1, r_2, t_3, r_4
    r_4 = int(message[2:7].hex(),16) # The payload starts after the 16-byte header
    t_1 = int(message[7:12].hex(),16)

    t1 = r_4 - t_1

    t2 = t_3 - r_2

    tof = (t1 - t2)/2

    distance = tof * UNIT_CONVERSION * SPEED_OF_LIGHT
    return distance

if __name__ == "__main__":
    
    init(PAN_ID, SRC_ADDR)

    print("searching")
    while True:
        isResponse = request_respond()
        if isResponse == True:
            print(times_message.hex())
            distance = get_distance(times_message)
            print(f"distance(m): {distance}")
        time.sleep_us(50)
