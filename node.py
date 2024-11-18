import dwmCom
import time
from machine import Pin
import uasyncio
from random import randint

class UWBNode:
    def __init__(self, pan, src, led_pin="LED", irq_pin_num=14):
        """
        Initialize the UWB receiver.
        
        Args:
            led_pin (str): Pin name for LED
            irq_pin_num (int): Pin number for IRQ
        """
        self.led = Pin(led_pin, Pin.OUT)
        self.irq_pin = Pin(irq_pin_num, Pin.IN)
        
        # Constants
        self.SPEED_OF_LIGHT = 299702547  # m/s
        self.UNIT_CONVERSION = 1.565e-11  # s
        self.DELAY = 65897.62
        
        # Instance variables for timestamps and messages
        self.r_2 = 0  # Reception timestamp 2
        self.t_3 = 0  # Transmission timestamp 3
        self.t_1 = 0  # Transmission timestamp 1
        self.r_4 = 0  # Reception timestamp 4
        self.success_tr = False
        self.success_times = False
        self.sequence = None
        self.times_message = bytearray([])
        self.pan = pan
        self.id = src
        self.handshake_results = []

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
        self.t_1 = dwmCom.get_tx_timestamp()
        self.r_4 = dwmCom.get_rx_timestamp()
        message = bytearray(dwmCom.read_register_intuitive(0x11, 5))
        sequence = message[2]
        if sequence == self.sequence:
            self.range_success = True
            self.led.toggle()

    def _handle_handshake_interrupt(self, pin):
        """Handle interrupt for handshake."""
        message = dwmCom.read_register(0x11, 18)
        dwmCom.toggle_buffer()
        dwmCom.search()
        message = bytearray(reversed(message))
        sequence = message[15]
        target_addr = int.from_bytes(message[7:9], 'big')
        if sequence == self.sequence and target_addr not in self.handshake_results:
            self.handshake_results.append(hex(target_addr))
            #self.led.toggle()

    def _handle_interrupt_times(self, pin):
        """Handle interrupt for timestamp reception."""
        self.times_message = bytearray(dwmCom.read_register_intuitive(0x11, 23))
        sequence_received = self.times_message[20]

        if sequence_received == self.sequence:
            self.success_times = True
            self.led.toggle()

    async def receive_times(self):
        """
        Receive timing data for a specific sequence number.
        
        Args:
            sequence (int): Sequence number to match
        
        Returns:
            bool: Success status
        """
        self.success_times = False
        
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_interrupt_times)

        count = 0
        while not self.success_times and count <= 200:
            dwmCom.search()
            await uasyncio.sleep_ms(5)
            count += 1

        return self.success_times
    
    async def twr(self, dest_addr):
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
        self.sequence = randint(0,255)
        dwmCom.format_message_mac(
            frame_type=1,
            seq_num=self.sequence,
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
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_twr_interrupt)
        
        dwmCom.transmit_and_wait()
        time.sleep_ms(1)

        if self.range_success:
            time.sleep_ms(5)
            time_received = await self.receive_times()

            return time_received
        return False
    
    async def handshake(self):
        """
        handshake to determine what node to range with.
        
        Args:
            pan_id (int): PAN identifier
            src_addr (int): Source address
            sequence_num (int): Sequence number
        
        Returns:
            bool: Success status
        """
        self.sequence = randint(0,255)
        dwmCom.format_message_mac(
            frame_type=1,
            seq_num=self.sequence,
            dest_pan_id=self.pan,
            dest_addr=0XFFFF,
            src_pan_id=self.pan,
            src_addr=self.id,
            payload='hello',
            security_enabled=False,
            frame_pending=False,
            ack_request=False,
            pan_id_compress=False
        )

        self.handshake_success = False

        dwmCom.transmit()
        time.sleep_ms(5)

        await self.init()
        dwmCom.set_receive_interrupt()
        dwmCom.enable_double_buffering()
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_handshake_interrupt)
        count = 0
        while count <= 150:
            dwmCom.search()
            await uasyncio.sleep_ms(5)
            count += 1

        if len(self.handshake_results) > 0:
            print(self.handshake_results)
            ranging_targets = self.handshake_results
            self.handshake_results = []
            return ranging_targets
        return None

    async def get_distance(self):
        """
        Calculate distance based on timestamps.
        
        Returns:
            float: Calculated distance in meters
        """
        self.r_2 = int(self.times_message[2:7].hex(), 16)
        self.t_3 = int(self.times_message[7:12].hex(), 16)

        t1 = self.r_4 - self.t_1
        t2 = self.t_3 - self.r_2

        tof = (t1 - t2 - self.DELAY) / 2
        distance = tof * self.UNIT_CONVERSION * self.SPEED_OF_LIGHT
        return distance

    async def get_calibration_data(self):
        """
        Get calibration data from timestamps.
        
        Returns:
            tuple: (t1, t2) timing values for calibration
        """
        self.r_4 = int(self.times_message[2:7].hex(), 16)
        self.t_1 = int(self.times_message[7:12].hex(), 16)

        t1 = self.r_4 - self.t_1
        t2 = self.t_3 - self.r_2

        return t1, t2

    async def start_ranging(self, dest_addr, callback=None):
        """
        Start continuous ranging measurements with optional callback.
        
        Args:
            callback (callable, optional): Function to call with distance measurements
        """
        is_response = False
        count = 0
        while not is_response and count < 5:
            is_response = await self.twr(dest_addr)
            if is_response:
                distance = await self.get_distance()
                if callback:
                    callback(distance, dest_addr)
            else: await self.init()
            count += 1

    async def start_calibration(self, num_samples=100):
        """
        Perform calibration measurements.
        
        Args:
            num_samples (int): Number of calibration samples to collect
        
        Returns:
            dict: Calibration data including timing measurements and calculated delay
        """
        calibration_data = {
            "t1": [],
            "t2": [],
            "delay": []
        }
        
        print("Starting calibration...")
        while len(calibration_data["t1"]) <= num_samples:
            is_response = await self.twr(0x1234)
            if is_response:
                t1, t2 = await self.get_calibration_data()
                calibration_data["t1"].append(t1)
                calibration_data["t2"].append(t2)
            await uasyncio.sleep_ms(50)
            
        return calibration_data

# Example usage:
async def main():
    # Example parameters
    PAN_ID = 0xB34A
    SRC_ADDR = 0x1234  # For receiver

    # Create receiver instance
    receiver = UWBNode(PAN_ID, SRC_ADDR)
    
    # Initialize
    await receiver.init()
    
    # Start continuous ranging
    def distance_callback(distance):
        print(f"Distance: {distance:.3f} m ({distance/.0254:.2f} in)")
    
    await receiver.start_ranging(0x1234, callback=distance_callback)

if __name__ == "__main__":
    uasyncio.run(main())