import dwmCom
from machine import Pin
import time
from random import randint
import uasyncio

class UWBTransmitter:
    def __init__(self, led_pin="LED", irq_pin_num=14):
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
        self.success = False
        self.times_success = False
        self.target_addr = None

    def int_to_bytes(self, n, byteorder='big'):
        """Convert integer to bytes with specified byte order."""
        if n == 0:
            return b'\x00'

        result = bytearray()
        while n > 0:
            result.append(n & 0xFF)
            n >>= 8

        if byteorder == 'big':
            reversed_result = []
            for i in range(len(result) - 1, -1, -1):
                reversed_result.append(result[i])
            result = reversed_result

        return bytes(result)

    async def init(self, pan_id, src_addr):
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
            pan_id=pan_id,
            device_address=src_addr,
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
            self.success = True
            self.led.toggle()

#sort out how to handle tag/node handshake
    def _handle_handshake_interrupt(self, pin):
        """Handle interrupt for handshake."""
        self.tx_time = dwmCom.get_tx_timestamp()
        self.rx_time = dwmCom.get_rx_timestamp()
        message = bytearray(dwmCom.read_register_intuitive(0x11, 5))
        sequence = message[2]
        self.target_addr = message[9:10]
        print(self.target_addr)
        if sequence == self.current_sequence:
            self.success = True
            self.led.toggle()

    def _handle_times_interrupt(self, pin):
        """Handle interrupt for time data transmission."""
        message = bytearray(dwmCom.read_register_intuitive(0x11, 5))
        sequence = message[2]
        if sequence == self.current_sequence:
            self.times_success = True
            self.led.toggle()

    async def send_times(self, tx, rx, dest_addr, sequence_num, src_addr, pan_id):
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
        tx_bytes = self.int_to_bytes(tx, byteorder='little')
        tx_bytes = tx_bytes + (b'\x00' * (5 - len(tx_bytes)))
        message.extend(tx_bytes)
        
        # Format rx timestamp (5 bytes)
        rx_bytes = self.int_to_bytes(rx, byteorder='little')
        rx_bytes = rx_bytes + (b'\x00' * (5 - len(rx_bytes)))
        message.extend(rx_bytes)

        dwmCom.format_message_mac(
            frame_type=1,
            seq_num=sequence_num,
            dest_pan_id=pan_id,
            dest_addr=dest_addr,
            src_pan_id=pan_id,
            src_addr=src_addr,
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

    async def twr(self, pan_id, src_addr, dest_addr, sequence_num):
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
            dest_pan_id=pan_id,
            dest_addr=dest_addr,
            src_pan_id=pan_id,
            src_addr=src_addr,
            payload='hello',
            security_enabled=False,
            frame_pending=False,
            ack_request=True,
            pan_id_compress=False
        )

        dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
        dwmCom.write_register(0x0E, b'\x00\x40\x00\x00')

        self.success = False
        self.current_sequence = sequence_num
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_twr_interrupt)
        
        dwmCom.transmit_and_wait()
        time.sleep_ms(1)

        if self.success:
            time_sent = await self.send_times(
                self.tx_time, 
                self.rx_time, 
                dest_addr,
                sequence_num, 
                src_addr, 
                pan_id
            )
            return time_sent
        return False

    async def handshake(self, pan_id, src_addr, sequence_num):
        """
        handshake to determine what node to range with.
        
        Args:
            pan_id (int): PAN identifier
            src_addr (int): Source address
            sequence_num (int): Sequence number
        
        Returns:
            bool: Success status
        """
        dwmCom.format_message_mac(
            frame_type=1,
            seq_num=sequence_num,
            dest_pan_id=pan_id,
            dest_addr=0XFFFF,
            src_pan_id=pan_id,
            src_addr=src_addr,
            payload='hello',
            security_enabled=False,
            frame_pending=False,
            ack_request=True,
            pan_id_compress=False
        )

        dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
        dwmCom.write_register(0x0E, b'\x00\x40\x00\x00')

        self.success = False
        self.current_sequence = sequence_num
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_handshake_interrupt)
        
        dwmCom.transmit_and_wait()
        time.sleep_ms(1)

        if self.success:
            time_sent = await self.send_times(
                self.tx_time, 
                self.rx_time, 
                self.target_addr,
                sequence_num, 
                src_addr, 
                pan_id
            )
            return time_sent
        return False

# Example usage:
async def main():
    # Example parameters
    PAN_ID = 0xB34A
    SRC_ADDR = 0x5678
    DEST_ADDR = 0x1234

    # Create transmitter instance
    transmitter = UWBTransmitter()
    
    # Initialize
    await transmitter.init(PAN_ID, SRC_ADDR)
    
    # Main loop
    while True:
        sequence_num = randint(0, 255)
        result = await transmitter.twr(PAN_ID, SRC_ADDR, DEST_ADDR, sequence_num)
        print(result)
        if result == False:
            await transmitter.init(PAN_ID, DEST_ADDR)
        await uasyncio.sleep(0.5)

if __name__ == "__main__":
    uasyncio.run(main())