import dwmCom
from machine import Pin
import time
from random import randint
import uasyncio

class UWBTag:
    def __init__(self, pan, id, led_pin="LED", irq_pin_num=14):
        """
        Initialize the UWB transmitter.
        
        Args:
            led_pin (str): Pin name for LED
            irq_pin_num (int): Pin number for IRQ
        """
        self.led = Pin(led_pin, Pin.OUT)
        self.irq_pin = Pin(irq_pin_num, Pin.IN)
        self.tx_time = None
        self.rx_time = None
        self.range_sucess = False
        self.times_success = False
        self.handshake_init = False
        self.handshake_complete = False
        self.target_addr = None
        self.pan = pan
        self.id = id

    async def init(self):
        """
        Initialize the UWB radio with specified PAN ID and source address.
        
        Args:
            pan_id (int): PAN identifier
            src_addr (int): Source address
        """
        dwmCom.reset()
        dwmCom.setup_radio()
        dwmCom.lde_load()
        dwmCom.init_frame_control(
            pan_id=self.pan,
            device_address=self.id,
            enable_beacon=True,
            enable_data=True,
            enable_ack=True,
            enable_mac_cmd=False,
            is_coordinator=False,
            enable_reserved=False
        )

    def _handle_twr_interrupt(self, pin):
        """Handle interrupt for TWR transmission."""
        self.tx_time = dwmCom.get_tx_timestamp()
        self.rx_time = dwmCom.get_rx_timestamp()
        message = bytearray(dwmCom.read_register_intuitive(0x11, 5))
        sequence = message[2]
        if sequence == self.current_sequence:
            self.range_success = True
            self.led.toggle()

    def _handle_interrupt_handshake(self, pin):
        """Handle interrupt for two-way handshake response."""

        message = bytearray(dwmCom.read_register_intuitive(0x11, 18))

        self.sequence = message[15]

        self.target_addr = int.from_bytes(message[7:9], 'big')

        self.handshake_init = True

    def _send_handshake_interrupt(self, pin):
        self.handshake_complete = True

    def _handle_times_interrupt(self, pin):
        """Handle interrupt for time data transmission."""
        message = bytearray(dwmCom.read_register_intuitive(0x11, 5))
        sequence = message[2]
        if sequence == self.current_sequence:
            self.times_success = True
            self.led.toggle()

    async def send_handshake(self):
        dwmCom.format_message_mac(
            frame_type=1,
            seq_num=self.sequence,
            dest_pan_id=self.pan,
            dest_addr=self.target_addr,
            src_pan_id=self.pan,
            src_addr=self.id,
            payload='hello',
            security_enabled=False,
            frame_pending=False,
            ack_request=False,
            pan_id_compress=False
        )
        rand = randint(0,50)
        delay = 0.01*rand
        await uasyncio.sleep(delay)
        dwmCom.transmit()
        await uasyncio.sleep_ms(5)
        self.led.toggle()

    async def send_times(self, tx, rx, dest_addr, sequence_num):
        """
        Send timestamp data to destination.
        
        Args:
            tx (int): Transmission timestamp
            rx (int): Reception timestamp
            dest_addr (int): Destination address
            sequence_num (int): Sequence number
            src_addr (int): Source address
            pan_id (int): PAN identifier
        
        Returns:
            bool: Success status
        """
        message = bytearray()
        
        # Format tx timestamp (5 bytes)
        tx_bytes = dwmCom.int_to_bytes(tx, byteorder='little')
        tx_bytes = tx_bytes + (b'\x00' * (5 - len(tx_bytes)))
        message.extend(tx_bytes)
        
        # Format rx timestamp (5 bytes)
        rx_bytes = dwmCom.int_to_bytes(rx, byteorder='little')
        rx_bytes = rx_bytes + (b'\x00' * (5 - len(rx_bytes)))
        message.extend(rx_bytes)

        dwmCom.format_message_mac(
            frame_type=1,
            seq_num=sequence_num,
            dest_pan_id=self.pan,
            dest_addr=dest_addr,
            src_pan_id=self.pan,
            src_addr=self.id,
            payload=message,
            security_enabled=False,
            frame_pending=False,
            ack_request=True,
            pan_id_compress=False
        )

        self.current_sequence = sequence_num
        self.times_success = False
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_times_interrupt)
        
        dwmCom.transmit_and_wait()
        time.sleep_ms(1)

        return self.times_success

    async def twr(self, dest_addr, sequence_num):
        """
        Perform Two-Way Ranging (TWR).
        
        Args:
            pan_id (int): PAN identifier
            src_addr (int): Source address
            dest_addr (int): Destination address
            sequence_num (int): Sequence number
        
        Returns:
            bool: Success status
        """
        dwmCom.format_message_mac(
            frame_type=1,
            seq_num=sequence_num,
            dest_pan_id=self.pan,
            dest_addr=dest_addr,
            src_pan_id=self.pan,
            src_addr=self.id,
            payload='hello',
            security_enabled=False,
            frame_pending=False,
            ack_request=True,
            pan_id_compress=False
        )

        dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
        dwmCom.set_receive_interrupt()

        self.range_success = False
        self.current_sequence = sequence_num
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_twr_interrupt)
        
        dwmCom.transmit_and_wait()
        time.sleep_ms(1)

        if self.range_success:
            time_sent = await self.send_times(
                self.tx_time, 
                self.rx_time, 
                dest_addr,
                sequence_num
            )
            return time_sent
        return False
    
    async def handshake_response(self):
        """
        Perform two-way ranging response.
        
        Returns:
            bool: Success status
        """
        dwmCom.init_ack_timing(ack_time=6)
        dwmCom.init_auto_ack(auto_ack=False, rx_auth=True)
        dwmCom.set_receive_interrupt()

        self.handshake_init = False
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_interrupt_handshake)

        count = 0
        while not self.handshake_init and count <= 200:
            dwmCom.search()
            await uasyncio.sleep_ms(5)
            count += 1

        if self.handshake_init:
            #print('handshake init received')
            await self.init()
            dwmCom.set_send_interrupt()
            self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._send_handshake_interrupt)
            self.handshake_complete = False
            await uasyncio.sleep_ms(50)
            await self.send_handshake()
            return self.handshake_complete
        
        return False
    
    async def start_handshake(self, callback=None):
        """
        Start continuous ranging measurements with optional callback.
        
        Args:
            callback (callable, optional): Function to call with distance measurements
        """
        print("looking for handshake")
        while True:
            is_response = await self.handshake_response()
            if is_response == True:
                print('handshake received and response sent')
            else: print('handshake not received')
            await uasyncio.sleep_ms(50)

# Example usage:
async def main():
    # Example parameters
    PAN_ID = 0xB34A
    SRC_ADDR = 0x5678
    DEST_ADDR = 0x1234

    # Create transmitter instance
    transmitter = UWBTag(PAN_ID,SRC_ADDR)
    
    # Initialize
    await transmitter.init()
    
    # Main loop
    while True:
        sequence_num = randint(0, 255)
        result = await transmitter.twr(DEST_ADDR, sequence_num)
        print(result)
        if result == False:
            await transmitter.init()
        await uasyncio.sleep(0.5)

if __name__ == "__main__":
    uasyncio.run(main())