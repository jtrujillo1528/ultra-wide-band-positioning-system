import dwmCom
import time
from machine import Pin
import uasyncio
import random

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
        self.handshake_init = False
        self.handshake_complete = False
        self.success_times = False
        self.sequence = None
        self.times_message = bytearray([])
        self.pan = pan
        self.id = src

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

    def _handle_interrupt_tr(self, pin):
        """Handle interrupt for two-way ranging response."""
        self.r_2 = dwmCom.get_rx_timestamp()
        self.t_3 = dwmCom.get_tx_timestamp()

        message = bytearray(dwmCom.read_register_intuitive(0x11, 18))
        print(message.hex())
        self.sequence = message[15]
        self.success_tr = True

    def _handle_interrupt_handshake(self, pin):
        """Handle interrupt for two-way handshake response."""

        message = bytearray(dwmCom.read_register_intuitive(0x11, 18))
        #print(message.hex())
        self.sequence = message[15]
        #print(hex(self.sequence))
        self.target_addr = int.from_bytes(message[7:9], 'big')
        #print(hex(self.target_addr))
        self.handshake_init = True

    def _handle_interrupt_times(self, pin):
        """Handle interrupt for timestamp reception."""
        self.times_message = bytearray(dwmCom.read_register_intuitive(0x11, 23))
        sequence_received = self.times_message[20]

        if sequence_received == self.sequence:
            self.success_times = True
            self.led.toggle()

    def _send_handshake_interrupt(self, pin):
        #print("message sent")
        self.handshake_complete = True

    async def send_handshake(self):
        #print('attempting to send handshake')
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
        rand = random.randint(0,50)
        delay = 0.01*rand
        await uasyncio.sleep(delay)
        dwmCom.transmit()
        await uasyncio.sleep_ms(5)
        self.led.toggle()

    async def receive_times(self, sequence):
        """
        Receive timing data for a specific sequence number.
        
        Args:
            sequence (int): Sequence number to match
        
        Returns:
            bool: Success status
        """
        self.success_times = False
        self.sequence = sequence
        
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_interrupt_times)

        count = 0
        while not self.success_times and count <= 200:
            dwmCom.search()
            await uasyncio.sleep_ms(5)
            count += 1

        return self.success_times

    async def twr_response(self):
        """
        Perform two-way ranging response.
        
        Returns:
            bool: Success status
        """
        dwmCom.init_ack_timing(ack_time=6)
        dwmCom.init_auto_ack(auto_ack=True, rx_auth=True)
        dwmCom.set_send_interrupt()

        self.success_tr = False
        self.irq_pin.irq(trigger=Pin.IRQ_RISING, handler=self._handle_interrupt_tr)

        count = 0
        while not self.success_tr and count <= 200:
            dwmCom.search()
            await uasyncio.sleep_ms(5)
            count += 1

        if self.success_tr:
            result = await self.receive_times(self.sequence)
            return result
        
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

    async def get_distance(self):
        """
        Calculate distance based on timestamps.
        
        Returns:
            float: Calculated distance in meters
        """
        self.r_4 = int(self.times_message[2:7].hex(), 16)
        self.t_1 = int(self.times_message[7:12].hex(), 16)

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

    async def start_continuous_ranging(self, callback=None):
        """
        Start continuous ranging measurements with optional callback.
        
        Args:
            callback (callable, optional): Function to call with distance measurements
        """
        print("Starting continuous ranging...")
        while True:
            is_response = await self.twr_response()
            if is_response:
                distance = await self.get_distance()
                if callback:
                    callback(distance)
            await uasyncio.sleep_ms(50)

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
            is_response = await self.twr_response()
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
    
    await receiver.start_continuous_ranging(callback=distance_callback)

if __name__ == "__main__":
    uasyncio.run(main())