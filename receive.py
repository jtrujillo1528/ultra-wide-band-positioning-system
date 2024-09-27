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
    dwmCom.write_register(0x0E,b'\x80\x00\x00\x00')
    dwmCom.setup_radio()
    dwmCom.init_ack_timing(ack_time=6)
    dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
    print('searching...')
    while True:
        dwmCom.search()
        time.sleep_us(200)
main()