import dwmCom
from machine import Pin
import time
import random

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x5678 #update for src

'''def handle_interrupt(pin):
    #time.sleep(0.1)
    print(f"sent: {dwmCom.get_tx_timestamp()}")
    print(f"received: {dwmCom.get_rx_timestamp()}")
    temp = bytearray(dwmCom.read_register_intuitive(0x11,5))
    print(temp[2])
    led.toggle()  # Toggle LED to visually indicate transmission

irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)'''

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

def twr(dest_addr, sequence_num):
    global success
    dwmCom.format_message_mac(
        frame_type=1,  # 1 for Data
        seq_num=sequence_num,
        dest_pan_id=PAN_ID,
        dest_addr= dest_addr, #update for addr
        src_pan_id=PAN_ID,
        src_addr=SRC_ADDR,
        payload='hello',
        security_enabled=False,
        frame_pending=False,
        ack_request=True,
        pan_id_compress=False
    )

    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    dwmCom.write_register(0x0E,b'\x00\x40\x00\x00')

    success = False

    def handle_interrupt(pin):
        global tx_time, rx_time, success
        time.sleep(0.1)
        tx_time = dwmCom.get_tx_timestamp()
        rx_time = dwmCom.get_rx_timestamp()
        message = bytearray(dwmCom.read_register_intuitive(0x11,5))
        sequence = message[2]
        if sequence == sequence_num:
            success = True
            led.toggle()  # Toggle LED to visually indicate transmission

    irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)
    attempts = 0
    while success == False and attempts <= 3:
        dwmCom.transmit_and_wait()
        time.sleep(0.05)
        attempts +=1
    return success

def send_times(tx, rx, dest_addr, sequence_num):
    message = bytearray()
    tx_bytes = int_to_bytes(tx)
    rx_bytes = int_to_bytes(rx)
    message.extend(bytes([74]))
    message.extend(tx_bytes)
    message.extend(bytes([72]))
    message.extend(rx_bytes)
    message.extend(bytes([78]))
    dwmCom.format_message_mac(
        frame_type=1,  # 1 for Data
        seq_num=sequence_num,
        dest_pan_id=PAN_ID,
        dest_addr= dest_addr, #update for addr
        src_pan_id=PAN_ID,
        src_addr=SRC_ADDR,
        payload=message,
        security_enabled=False,
        frame_pending=False,
        ack_request=True,
        pan_id_compress=False
)

if __name__ == "__main__":
    dwmCom.reset()
    dwmCom.setup_radio()
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
    num = random.randint(0,255)
    result = twr(0x1234,num)
    if result == True:
        send_times(tx_time, rx_time, 0x1234,num)

