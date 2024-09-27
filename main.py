import dwmCom
import time
from machine import Pin

led = Pin("LED", Pin.OUT)  # Onboard LED on the Pico W
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x5678 #update for device

def handle_interrupt(pin):
    print(f"received: {dwmCom.get_rx_timestamp()}")
    print(f"sent: {dwmCom.get_tx_timestamp()}")
    '''    amp, noise = dwmCom.get_rx_quality()
    print(f"amplitude (m): {amp}")
    print(f"noise (dB) : {noise}")'''
    led.toggle()  # Toggle LED to visually indicate transmission
    #print(dwmCom.read_register_intuitive(0x09,16).hex())

    


irq_pin.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)

def main():
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
    dwmCom.format_message_and_transmit(
        frame_type=1,  # 0 for Beacon
        seq_num=1,
        dest_pan_id=PAN_ID,
        dest_addr=0x1234, #update for device
        src_pan_id=PAN_ID,
        src_addr=SRC_ADDR,
        payload='hello',
        security_enabled=False,
        frame_pending=False,
        ack_request=False,
        pan_id_compress=False
    )
    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    dwmCom.setup_radio()
    print('searching...')
    while True:
        dwmCom.search()
        time.sleep_us(200)
main()