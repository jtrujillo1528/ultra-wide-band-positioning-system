# ble_handler.py
import ubluetooth
import struct
from micropython import const
import utime
import urandom

# Custom manufacturer ID and data
_CUSTOM_MFG_ID = const(0x0102)  # Replace with your assigned manufacturer ID if you have one

def generate_message_id():
    """Generate a simple unique identifier"""
    return '{:08x}'.format(urandom.getrandbits(32))

class BLEHandler:
    def __init__(self, name="PicoW"):
        self.name = name
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.message_ledger = []
        self.scan_result = None
    
    def advertise(self, message):
        # Parse the message
        parts = message.split(',')
        if len(parts) != 6:
            print("Invalid message format")
            return
        
        message_id, hop_count, t_1, t_2, src_addr, twr_src_addr = parts
        
        # Check if we've seen this message before
        if message_id in self.message_ledger:
            print("Message already processed")
            return
        
        # Add to ledger, removing oldest if necessary
        if len(self.message_ledger) >= 10:
            self.message_ledger.pop(0)
        self.message_ledger.append(message_id)
        
        # Decrement hop count
        hop_count = int(hop_count) - 1
        
        if hop_count >= 0:
            # Prepare the advertisement data
            mfg_data = struct.pack("<H", _CUSTOM_MFG_ID) + message.encode()
            payload = bytearray(b'\x02\x01\x06') + bytearray([len(mfg_data) + 1, 0xFF]) + mfg_data
            print(payload)
            
            # Start advertising
            self.ble.gap_advertise(100, adv_data=payload)
            print(f"Advertising: {message}")
            
            # Advertise for a short period (e.g., 500ms)
            utime.sleep_ms(500)
            
            # Stop advertising
            self.ble.gap_advertise(None)
        else:
            print("Hop count reached zero, not retransmitting")

    def scan_callback(self, addr_type, addr, adv_type, rssi, adv_data):
        print(f"Scan callback - Type: {adv_type}, RSSI: {rssi}, Data: {adv_data.hex()}")
        if adv_type == 0x03 and len(adv_data) > 5:
            mfg_id = struct.unpack("<H", adv_data[5:7])[0]
            print(f"Manufacturer ID: {mfg_id}")
            if mfg_id == _CUSTOM_MFG_ID:
                self.scan_result = adv_data[7:].decode()
                print(f"Decoded data: {self.scan_result}")

    def scan_and_process(self):
        self.scan_result = None
        self.ble.gap_scan(6000, 30000, 30000, True)
        utime.sleep_ms(2000)
        self.ble.gap_scan(None)

        if self.scan_result:
            print("ble packet received")
            parts = self.scan_result.split(',')
            if len(parts) == 6:
                message_id, hop_count, t_1, t_2, src_addr, twr_src_addr = parts
                if message_id not in self.message_ledger and int(hop_count) > 0:
                    print(f"Received new message: {self.scan_result}")
                    self.advertise(self.scan_result)
                else:
                    print("Message already processed or hop count zero")
            else:
                print("Invalid message format received")
        else:
            print("No valid messages received during scan")

def create_ble_message(hop_count, t_1, t_2, src_addr, twr_src_addr):
    message_id = generate_message_id()  # Generate a unique identifier
    return f"{message_id},{hop_count},{t_1},{t_2},{src_addr},{twr_src_addr}"