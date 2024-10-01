# ble_handler.py
import ubluetooth
import struct
from micropython import const
import utime

# Custom manufacturer ID and data
_CUSTOM_MFG_ID = const(0x0102)  # Replace with your assigned manufacturer ID if you have one

class BLEHandler:
    def __init__(self, name="PicoW"):
        self.name = name
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.message_ledger = []
    
    def advertise(self, message):
        # Parse the message
        parts = message.split(',')
        if len(parts) != 5:
            print("Invalid message format")
            return
        
        message_id, hop_count, t_1, t_2, src_addr = parts
        
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
            
            # Start advertising
            self.ble.gap_advertise(100, adv_data=payload)
            print(f"Advertising: {message}")
            
            # Advertise for a short period (e.g., 500ms)
            utime.sleep_ms(500)
            
            # Stop advertising
            self.ble.gap_advertise(None)
        else:
            print("Hop count reached zero, not retransmitting")

def create_ble_message(message_id, hop_count, t_1, t_2, src_addr):
    return f"{message_id},{hop_count},{t_1},{t_2},{src_addr}"