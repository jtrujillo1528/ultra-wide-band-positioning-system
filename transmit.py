import dwmCom
from machine import Pin
import time
from random import randint

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x5678 #update for src

def int_to_bytes(n, byteorder='big'):
    # Handle zero explicitly
    if n == 0:
        return b'\x00'

    result = bytearray()
    while n > 0:
        result.append(n & 0xFF)
        n >>= 8

    if byteorder == 'big':
        # Manually reverse the list for big-endian byte order
        reversed_result = []
        for i in range(len(result) - 1, -1, -1):
            reversed_result.append(result[i])
        result = reversed_result

    return bytes(result)

def twr(pan_id, src_addr, dest_addr, sequence_num):
    global success
    dwmCom.format_message_mac(
        frame_type=1,  # 1 for Data
        seq_num=sequence_num,
        dest_pan_id=pan_id,
        dest_addr= dest_addr, #update for addr
        src_pan_id=pan_id,
        src_addr=src_addr,
        payload='hello',
        security_enabled=False,
        frame_pending=False,
        ack_request=True,
        pan_id_compress=False
    )

    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)

    dwmCom.write_register(0x0E,b'\x00\x40\x00\x00')

    success = False

    def handle_interrupt_twr(pin):
        global tx_time, rx_time, success
        tx_time = dwmCom.get_tx_timestamp()
        rx_time = dwmCom.get_rx_timestamp()
        message = bytearray(dwmCom.read_register_intuitive(0x11,5))
        sequence = message[2]
        if sequence == sequence_num:
            success = True
            led.toggle()  # Toggle LED to visually indicate transmission

    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt_twr)
    attempts = 0
    while success == False and attempts <= 5:
        dwmCom.transmit_and_wait()
        time.sleep_ms(1)
        attempts +=1
    time_sent = False
    if success == True:
        time_sent = send_times(tx_time, rx_time, dest_addr,sequence_num, src_addr, pan_id)
    return time_sent

def send_times(tx, rx, dest_addr, sequence_num, src_addr, pan_id):
    global times_success
    message = bytearray()
    message = bytearray()
    
    # Format tx timestamp (5 bytes)
    tx_bytes = int_to_bytes(tx, byteorder='little')
    tx_bytes = tx_bytes + (b'\x00' * (5 - len(tx_bytes)))  # Pad with zeros if less than 5 bytes
    message.extend(tx_bytes)  
    
    # Format rx timestamp (5 bytes)
    rx_bytes = int_to_bytes(rx, byteorder='little')
    rx_bytes = rx_bytes + (b'\x00' * (5 - len(rx_bytes)))  # Pad with zeros if less than 5 bytes
    message.extend(rx_bytes)

    dwmCom.format_message_mac(
        frame_type=1,  # 1 for Data
        seq_num=sequence_num,
        dest_pan_id=pan_id,
        dest_addr= dest_addr, #update for addr
        src_pan_id=pan_id,
        src_addr=src_addr,
        payload=message,
        security_enabled=False,
        frame_pending=False,
        ack_request=True,
        pan_id_compress=False
    )
    def handle_interrupt_times(pin):
        global times_success
        message = bytearray(dwmCom.read_register_intuitive(0x11,5))
        sequence = message[2]
        if sequence == sequence_num:
            times_success = True
            led.toggle()  # Toggle LED to visually indicate transmission
    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt_times)
    times_success = False
    attempts_times = 0
    while times_success == False and attempts_times <= 5:
        dwmCom.transmit_and_wait()
        time.sleep_ms(1)
        attempts_times +=1

    return times_success

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
def twr_transmit(pan_id, src_addr, dest_addr, sequence_num):
    twr_result = twr(pan_id, src_addr, dest_addr, sequence_num)
    return twr_result

if __name__ == "__main__":
    init(PAN_ID, 0x1234)
    num = randint(0,255)
    result = twr_transmit(PAN_ID, SRC_ADDR, 0x1234, num)
    print(result)
    if result == False:
        init(PAN_ID, 0x1234)
    time.sleep(2)


