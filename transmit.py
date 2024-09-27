import dwmCom
from machine import Pin
import time

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x5678 #update for src

def handle_interrupt(pin):
    time.sleep(0.1)
    print(f"sent: {dwmCom.get_tx_timestamp()}")
    print(f"received: {dwmCom.get_rx_timestamp()}") 
    led.toggle()  # Toggle LED to visually indicate transmission

irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)

def main():
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
    dwmCom.format_message_mac(
        frame_type=1,  # 0 for Beacon
        seq_num=1,
        dest_pan_id=PAN_ID,
        dest_addr=0x1234, #update for addr
        src_pan_id=PAN_ID,
        src_addr=SRC_ADDR,
        payload='hello',
        security_enabled=False,
        frame_pending=False,
        ack_request=True,
        pan_id_compress=False
    )
    #set interrupt pin to notify RPI of good frame receive
    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    dwmCom.write_register(0x0E,b'\x00\x40\x00\x00')
    #dwmCom.init_rx_timeout(19900)
    print("Sending message...")
    while True:
        dwmCom.transmit_and_wait()
        time.sleep(2)


main()