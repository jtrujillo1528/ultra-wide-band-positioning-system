import dwmCom
import time
from machine import Pin

led = Pin("LED", Pin.OUT)  # Onboard LED on the Pico W
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234

def handle_interrupt(pin):
    print(f"received: {dwmCom.get_rx_timestamp()}")
    print(f"sent: {dwmCom.get_tx_timestamp()}")
    led.toggle()
    #time.sleep_ms(1000)

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
    global t_1, r_4, success_times, times_message

    success_times = False

    def handle_interrupt_times(pin):
        global success_times, times_message
        print("times triggered")
        times_message = bytearray(dwmCom.read_register_intuitive(0x11,18))
        sequence_received = times_message[15]

        if sequence_received == sequence:
            print("times received")
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
    global rx_timestamp, tx_timestamp, success_tr, sequence, times_message

    dwmCom.init_ack_timing(ack_time=6)
    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    #set irq to message send
    dwmCom.write_register(0x0E,b'\x80\x00\x00\x00')

    success_tr = False

    def handle_interrupt_tr(pin):
        global rx_timestamp, tx_timestamp, success_tr, sequence

        print("request received")
        rx_timestamp = dwmCom.get_rx_timestamp()
        tx_timestamp = dwmCom.get_tx_timestamp()

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

def get_times(message):
    payload = message[2:]  # The payload starts after the 16-byte header
    print(payload.hex())
    if len(payload) >= 11 and payload[0] == 74 and payload[-1] == 78:  # Check for start and end markers
        tx_end = payload.index(72)  # Find the marker for RX timestamp
        t_1 = int.from_bytes(payload[1:tx_end], 'big')
        r_4 = int.from_bytes(payload[tx_end+1:-1], 'big')
        
        print(f"Received t_1: {t_1}")
        print(f"Received r_4: {r_4}")

        return t_1, r_4
    return None, None

if __name__ == "__main__":
    global message

    init(PAN_ID, SRC_ADDR)

    print("searching")
    while True:
        isResponse = request_respond()
        if isResponse == True:
            print(times_message)
            t_1, r_4 = get_times(times_message)
        time.sleep_us(50)
