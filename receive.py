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
    global t_1, r_4, success_times

    success_times = False

    def handle_interrupt_times(pin):
        global success_times

        print("triggered")
        message = bytearray(dwmCom.read_register_intuitive(0x11,18))
        sequence_received = message[15]

        if sequence_received == sequence:
            print(message)
            success_times = True
            led.toggle()

    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt_times)

    count = 0

    while success_times == False and count <= 800:
        last_time = time.ticks_ms()
        dwmCom.search()
        time.sleep_ms(5)
        count += 1

    return success_times



def timestamp_and_respond():
    global rx_timestamp, tx_timestamp, success_tr, sequence

    dwmCom.init_ack_timing(ack_time=6)
    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    #set irq to message send
    dwmCom.write_register(0x0E,b'\x80\x00\x00\x00')

    success_tr = False

    def handle_interrupt_tr(pin):
        global rx_timestamp, tx_timestamp, success_tr, sequence

        rx_timestamp = dwmCom.get_rx_timestamp()
        tx_timestamp = dwmCom.get_tx_timestamp()

        message = bytearray(dwmCom.read_register_intuitive(0x11,18))
        
        sequence = message[15]

        success_tr = True

        led.toggle()

    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt_tr)

    count = 0

    while success_tr == False and count <= 800:
        dwmCom.search()
        time.sleep_ms(5)
        count += 1

    if success_tr == True:
        result = receive_times(sequence)
        
    return result


def main():
    init(PAN_ID, SRC_ADDR)

    isResponse = timestamp_and_respond()

    print(isResponse)
'''def main():
    #set interrupt pin to notify RPI of good frame receive
    dwmCom.reset()
    dwmCom.lde_load()
    dwmCom.init_frame_control(
        pan_id=PAN_ID,
        device_address=SRC_ADDR,
        enable_beacon=True,
        enable_data=True,
        enable_ack=True,
        enable_mac_cmd=False,
        is_coordinator=False,
        enable_reserved=False
    )
    #set interrupt pin to notify RPI of good frame receive
    dwmCom.write_register(0x0E,b'\x80\x00\x00\x00')
    dwmCom.setup_radio()
    dwmCom.init_ack_timing(ack_time=6)
    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    print('searching...')
    while True:
        dwmCom.search()
        time.sleep_us(200)'''
main()