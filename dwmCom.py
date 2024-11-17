import time
from machine import Pin, SPI

# SPI configuration 
spi = SPI(0, baudrate=1000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs = Pin(17, Pin.OUT)  # Chip Select (CS) for the DWM1000
irq = Pin(14, Pin.IN)  # Interrupt (IRQ) pin for receiving events
rst = Pin(15, Pin.OUT)

led = Pin("LED", Pin.OUT)  # Onboard LED on the Pico W


def reset():
    """
    Hard reset of DWM1000
    
    """
    rst.value(0)
    time.sleep_ms(2)
    rst.value(1)
    time.sleep_ms(10)

def read_register(address, length):
    """
    Reads value from DWM1000 register

    :param address: Hexidecimal register ID
    :param length: Length of register being read (int)
    :return: Value stored in register as a byte or byte array (little endian)
    
    """
    cs.value(0)
    spi.write(bytes([address & 0x7f]))
    data = spi.read(length)
    cs.value(1)
    return bytes(data)

def write_register(address, data):
    """
    Writes value to DWM1000 register

    :param address: Hexidecimal register ID
    :param data: value to be written to register. Byte or byte array little endian

    """
    cs.value(0)
    spi.write(bytes([address | 0x80]))
    spi.write(bytes(data))  # Reverse byte order for writing
    cs.value(1)

def read_register_intuitive(address, length):
    """
    Reads a given register in the DWM1000 and returns it's contents in hexidecimal big endian format
    Useful for troubleshooting

    :param address: Hexidecimal register ID
    :param length: Length of register being read (int)
    :return: Value stored in register as a byte or byte array (big endian)

    """
    data = read_register(address, length)
    return bytes(reversed(data))

def read_and_display_register_bits(address, length, register_name):
    """
    Reads a given register in the DWM1000 and displays it's contents in hexidecimal big endian, hexidecimal little endian, and bytes big endian format
    Useful for troubleshooting

    :param address: Hexidecimal register ID
    :param length: Length of register being red
    :param register_name: Name of register to be read

    """
    # Read the register in little-endian (device native) format
    data_le = read_register(address, length)
    # Read the register in big-endian (intuitive) format
    data_be = read_register_intuitive(address, length)
    
    print(f"\n{register_name} Register (0x{address:02X}):")
    print(f"Hex value (little-endian, device native): 0x{data_le.hex()}")
    print(f"Hex value (big-endian, intuitive): 0x{data_be.hex()}")
    
    # Convert to binary string (already in big-endian order)
    binary_str = ''.join(f'{byte:08b}' for byte in data_be)
    
    # Print binary representation
    print("Binary value (big-endian):")
    for i, bit in enumerate(binary_str):
        if i > 0 and i % 8 == 0:
            print(" ", end="")  # Space between bytes
        if i > 0 and i % 32 == 0:
            print()  # New line every 32 bits
        print(bit, end="")
    print("\n")

def read_subregister(register, offset, register_length, sub_length):
    full_data = read_register(register,register_length)    
    # Extract the required bytes
    subregister_data = full_data[offset:offset+sub_length]
    
    # Return the data (already in little-endian format)
    return bytes(subregister_data)

def write_subregister(register, offset, data, register_length, data_length):
    """
    Write a given value to a subregister in the DWM1000
    
    :param register: Hexidecimal register ID
    :param offset: Hexidecimal value of the sub-register offset with main register
    :param data: Value being written to sub-register (str, int, hex, or bytes)
    :param register_length: Length of register (int)
    :param data_length: Integer value of length of data in bytes being writted to sub-register

    """
    # Convert data to little-endian bytes
    if isinstance(data, str):
        if data.startswith('0x'):
            # Convert hex string to integer
            int_data = int(data, 16)
        else:
            # Assume it's a decimal string
            int_data = int(data)
        # Convert to little-endian bytes
        data_bytes = int_data.to_bytes(data_length, 'little')
    elif isinstance(data, int):
        # Convert integer to little-endian bytes
        data_bytes = data.to_bytes(data_length, 'little')
    elif isinstance(data, bytes):
        # Assume it's in big-endian, so reverse it
        data_bytes = data[::-1]
    else:
        raise ValueError("Data must be a hex string, an integer, or bytes")

    # Read the entire register
    full_register = bytearray(read_register(register, register_length))
    
    # Update only the specific bytes in the full register data
    full_register[offset:offset+data_length] = data_bytes
    
    # Write the entire updated register back
    write_register(register, full_register)

def write_bit(register_value, bit_index, bit_value):
    """
    Write a bit in a given register value.
    
    :param register_value: Bytes object containing the current register value
    :param bit_index: Index of the bit to write (0-31, where 0 is LSB)
    :param bit_value: Value to write (0 or 1)
    :return: Updated register value as bytes object

    """
    if bit_value not in (0, 1):
        raise ValueError("Bit value must be 0 or 1")
    
    # Convert bytes to integer
    value = int.from_bytes(register_value, 'little')
    
    if bit_value:
        # Set the bit
        value |= (1 << bit_index)
    else:
        # Clear the bit
        value &= ~(1 << bit_index)
    
    # Convert back to bytes
    return value.to_bytes(len(register_value), 'little')

def read_bit(register_value, bit_index):
    """
    Read a bit from a given register value.
    
    :param register_value: Bytes object or array of Bytes objects containing the current register value
    :param bit_index: Index of the bit to read (0-31, where 0 is LSB)
    :return: Value of the bit (0 or 1)

    """
    
    # Convert bytes to integer
    value = int.from_bytes(register_value, 'little')
    
    # Extract the bit
    return (value >> bit_index) & 1

def clear_status_bits(register,bits_to_clear):
    """
    Clear specific status bits in a given register.

    :param register: hexidecimal register ID
    :param bits_to_clear: A list of bit indices to clear (0-39)

    """
    # Create the bitmask
    bitmask = 0
    for bit in bits_to_clear:
        if 0 <= bit <= 39:
            bitmask |= (1 << bit)
        else:
            print(f"Warning: Bit {bit} is out of range and will be ignored.")
    
    # Convert the bitmask to bytes (little-endian)
    clear_mask = bitmask.to_bytes(5, 'little')
    
    # Write the bitmask to register 0x0F
    write_register(register, clear_mask)
    
def get_tx_status():
    """
    Displays status of DWM1000 transmitter

    :return: status of TX indicators
    
    """
    # Read the SYS_STATUS register (0x0F)
    sys_status = read_register(0x0F, 5)
    
    # Extract the relevant bits
    txfrb = (sys_status[0] >> 4) & 1  # Bit 4
    txprs = (sys_status[0] >> 5) & 1  # Bit 5
    txphs = (sys_status[0] >> 6) & 1  # Bit 6
    txfrs = (sys_status[0] >> 7) & 1  # Bit 7
    
    return {
        'TXFRB': txfrb,  # Transmit Frame Begins
        'TXPRS': txprs,  # Transmit Preamble Sent
        'TXPHS': txphs,  # Transmit PHY Header Sent
        'TXFRS': txfrs   # Transmit Frame Sent
    }
def address_to_bytes(addr):
    """
    Helper function to convert address to bytes and determine its length

    :param addr: address to be converted
    :return: address in bytes and its length

    """
    if isinstance(addr, int):
        if addr <= 0xFFFF:
            return addr.to_bytes(2, 'little'), 2
        else:
            return addr.to_bytes(8, 'little'), 8
    elif isinstance(addr, bytes):
        return addr, len(addr)
    else:
        raise ValueError("Address must be int or bytes")
    
def init_frame_control(pan_id, device_address, enable_beacon=True, enable_data=True, enable_ack=True, enable_mac_cmd=True, is_coordinator=False, enable_reserved=False):
    """
    Initialize frame control settings.
    
    :param pan_id_hex: PAN identifier in hexadecimal format (e.g., '0xDECA')
    :param device_address_hex: Device address in hexadecimal format (e.g., '0x1234' for short address or '0x1234567890ABCDEF' for extended address)
    :param enable_beacon: Enable Beacon frame reception
    :param enable_data: Enable Data frame reception
    :param enable_ack: Enable Acknowledgment frame reception
    :param enable_mac_cmd: Enable MAC command frame reception
    :param is_coordinator: Set to True if device is a coordinator
    :param enable_reserved: Enable reception of reserved frame types

    """
    
    # Set FEEN (Frame Filtering Enable) bit in register 0x04
    sys_cfg = read_register(0x04, 4)
    sys_cfg = int.from_bytes(sys_cfg, 'little')
    sys_cfg |= (1 << 0)  # Set bit 0 (FFEN)
    
    # Set frame filtering configuration bits
    sys_cfg |= (int(enable_beacon) << 2)     # FFAB
    sys_cfg |= (int(enable_data) << 3)       # FFAD
    sys_cfg |= (int(enable_ack) << 4)        # FFAA
    sys_cfg |= (int(enable_mac_cmd) << 5)    # FFAM
    sys_cfg |= (int(is_coordinator) << 1)    # FFBC
    sys_cfg |= (int(enable_reserved) << 6)   # FFAR
    sys_cfg |= (int(enable_reserved) << 7)   # FFA4
    sys_cfg |= (int(enable_reserved) << 8)   # FFA5
    
    # Write updated configuration to register 0x04
    write_register(0x04, sys_cfg.to_bytes(4, 'little'))
    
    # Set PAN identifier in register 0x03
    write_subregister(0x03, 2, pan_id, 4, 2)
    
    dev_addr_bytes, dev_addr_len = address_to_bytes(device_address)
    # Set device address
    if dev_addr_len == 2:
        # Short address (16-bit)
        write_subregister(0x03, 0, device_address, 4, 2)
    elif dev_addr_len == 8:
        # Extended address (64-bit)
        write_register(0x01, device_address.to_bytes(8, 'little'))
    else:
        raise ValueError("Device address must be either 2 bytes (short) or 8 bytes (extended)")

def init_auto_ack(auto_ack=True, rx_auth=True):
    sys_config = read_register(0x04,4)

    if auto_ack:
        sys_config = write_bit(sys_config,30,1)
    elif auto_ack == False:
        sys_config = write_bit(sys_config,30,0)
    
    if rx_auth:
       sys_config = write_bit(sys_config,29,1)
    elif not rx_auth:
        sys_config = write_bit(sys_config, 29, 0)

    write_register(0x04,sys_config)
    

def format_message_mac(frame_type, seq_num, dest_pan_id, dest_addr, src_pan_id, src_addr, payload, security_enabled=False, frame_pending=False, ack_request=False, pan_id_compress=False):
    """
    Format a message according to IEEE 802.15.4 standard.
    
    :param frame_type: 0 for Beacon, 1 for Data, 2 for Acknowledgment, 3 for MAC Command
    :param seq_num: Sequence number (0-255)
    :param dest_pan_id: Destination PAN ID (2 bytes)
    :param dest_addr: Destination address (int or bytes, 2 or 8 bytes)
    :param src_pan_id: Source PAN ID (2 bytes)
    :param src_addr: Source address (int or bytes, 2 or 8 bytes)
    :param payload: Message payload (bytes)
    :param security_enabled: Boolean, set True if security is enabled
    :param frame_pending: Boolean, set True if more data is pending
    :param ack_request: Boolean, set True if acknowledgment is required
    :param pan_id_compress: Boolean, set True to use PAN ID compression
    :return: Formatted message as bytes

    """

    fc = (frame_type & 0x07)  
    fc |= (security_enabled << 3)
    fc |= (frame_pending << 4)
    fc |= (ack_request << 5)
    fc |= (pan_id_compress << 6)

    # Destination Addressing Mode
    dest_addr_bytes, dest_addr_len = address_to_bytes(dest_addr)
    if dest_addr_len == 2:
        fc |= (0x02 << 10)  # Short Address
    elif dest_addr_len == 8:
        fc |= (0x03 << 10)  # Extended Address
    
    # Source Addressing Mode
    src_addr_bytes, src_addr_len = address_to_bytes(src_addr)
    if src_addr_len == 2:
        fc |= (0x02 << 14)  # Short Address
    elif src_addr_len == 8:
        fc |= (0x03 << 14)  # Extended Address

    
    # Assemble the frame
    frame = bytearray()
    frame.extend(fc.to_bytes(2, 'little'))  # Frame Control

    frame.append(seq_num)  # Sequence Number
    
    frame.extend(dest_pan_id.to_bytes(2, 'little'))  # Destination PAN ID

    frame.extend(dest_addr_bytes)  # Destination Address
    
    if not pan_id_compress:
        frame.extend(src_pan_id.to_bytes(2, 'little'))  # Source PAN ID
    frame.extend(src_addr_bytes)  # Source Address
    
    # Add payload
    frame.extend(payload)

    # Calculate total frame length (including 2 bytes for FCS)
    frame_length = len(frame) + 2

    # Write frame length to register 0x08 (TX_FCTRL)
    write_subregister(0x08, 0x00, frame_length, 5, 1)
    # Write message to TX buffer (0x09)
    write_register(0x09, frame)
    #print(read_register_intuitive(0x09,frame_length).hex())
    
    return frame

def transmit():
    """
    Function to transmit a message in the DWM1000

    """
    # Set TXSTRT in SYS_CTRL register (0x0D)
    sys_ctrl = read_register(0x0D, 4)
    sys_ctrl_new = write_bit(sys_ctrl,1,1)
    write_register(0x0D, sys_ctrl_new)

def transmit_and_wait():
    """
    Function to transmit a message and automatically enter reception mode in the DWM1000

    """
    sys_ctrl = read_register(0x0D,4)
    sys_ctrl_new = write_bit(sys_ctrl,7,1)
    sys_ctrl_new = write_bit(sys_ctrl_new,1,1)
    write_register(0x0D,sys_ctrl_new)

def get_rx_status():
    """
    Displays status of DWM1000 receiver

    :return: status of RX indicators
    
    """
    # Read the SYS_STATUS register (0x0F)
    sys_status = read_register(0x0F, 5)
    
    # Convert to integer for easier bit manipulation
    status_int = int.from_bytes(sys_status, 'little')
    
    return {
        'RXPRD': (status_int >> 8) & 1,    # Bit 8: Receiver Preamble Detected
        'RXSFDD': (status_int >> 9) & 1,   # Bit 9: Receiver SFD Detected
        'LDEDONE': (status_int >> 10) & 1, # Bit 10: LDE Processing Done
        'RXPHD': (status_int >> 11) & 1,   # Bit 11: Receiver PHY Header Detect
        'RXPHE': (status_int >> 12) & 1,   # Bit 12: Receiver PHY Header Error
        'RXDFR': (status_int >> 13) & 1,   # Bit 13: Receiver Data Frame Ready
        'RXFCG': (status_int >> 14) & 1,   # Bit 14: Receiver FCS Good
        'RXFCE': (status_int >> 15) & 1,   # Bit 15: Receiver FCS Error
        'RXRFSL': (status_int >> 16) & 1,  # Bit 16: Receiver Reed Solomon Frame Sync Loss
        'RXRFTO': (status_int >> 17) & 1,  # Bit 17: Receiver Frame Wait Timeout
        'LDEERR': (status_int >> 18) & 1,  # Bit 18: Leading Edge Detection Processing Error
        'RXOVRR': (status_int >> 20) & 1,  # Bit 20: Receiver Overrun
        'RXPTO': (status_int >> 21) & 1,   # Bit 21: Preamble Detection Timeout
    }
    
def setup_radio():
    """
    Sets up radio for transmission and reception

    -Initializes rx and tx to chanel 5, 6.8 Mbps data rate, standard SFD configuration, 16MHz PRF, 64 symbol preamble, and a PAC size of 8
    -Initializes interrupt pins to notify Pico W of successful message transmission and good frame reception
    -Sets up smart transmit power
    -Sets up transmission frame control

    """
    #initialize digital receiver configuration for 6.8 Mbps data rate, standard SFD configuration, 16 MHz PRF, 64 symbol preamble, PAC size of 8, P code of 4
    write_subregister(0x27,0x02,0x0001,45,2)
    write_subregister(0x27,0x04,0x0087,45,2)
    write_subregister(0x27,0x06, 0x0010,45,2)
    write_subregister(0x27, 0x08, 0x311A002D, 45, 4)
    write_subregister(0x27,0x26,0x0010,45,2)

    #tune agc for 6.8 mbps and 16 MHz
    write_subregister(0x23,0x04,0x8870,32,2)
    write_subregister(0x23,0x0C,0x2502A907,32,4)
    write_subregister(0x23,0x12,0x0055,32,2)
    #set analog RX control register
    write_subregister(0x28,0x0B,0xD8,51,1)
    #set RF_TXCTRL to chanel 5
    write_subregister(0x28,0x0C,0x001E3FE0,51,4)

    # The desired configuration
    desired_config = 0x21040055  # 00100001 00000100 00000000 01010101 in binary

    # Write the configuration to the CHAN_CTRL register (0x1F)
    write_register(0x1F, desired_config.to_bytes(4, 'little'))

    #set FS_PLLCFG value for chanel 5
    write_subregister(0x2B, 0x07, 0x0800041D, 21,4)
    #set FS_PLLTUNE value for chanel 5
    write_subregister(0x2B, 0x0B, 0xA6, 21, 1)

    #set TC_PGCDELAY for chanel 5
    write_subregister(0x2A, 0x0B, 0xC0, 12, 1)
     #set transmission power control for chanel 5, smart transmit power
    config = 0x0e082848
    write_register(0x1E,config.to_bytes(4,'little'))

    #setup transmission frame control
    tfc = read_register(0x08,5)

    bits = {
        'index': [13,14,15,16,17,18,19,20,21],
        'val': [0,1,1,1,0,1,0,0,0]
    }
    for i in range(len(bits['index'])):
        tfc = write_bit(tfc, bits['index'][i], bits['val'][i])
    write_register(0x08,tfc)

def lde_load():
    """
    Set LDE interface and load LDE microcode for leading edge detection and RX timestamping
    
    """
    #LDE configuration
    write_subregister(0x2E,0x1806,0x1607,10246,2)

    #LDE replica coefficient configuration
    write_subregister(0x2E,0x2804,0x428E,10246,2)

    write_subregister(0x36,0x00,0x0301,43,2)
    write_subregister(0x2D,0x06,0x8000,18,2)
    time.sleep_us(150)
    write_subregister(0x36,0x00,0x0200,43,2)

def search():
    """
    Search for compatible UWB signals
    
    """
    # Set RX_enab in SYS_CTRL register (0x0D)
    sys_ctrl = read_register(0x0D, 4)
    sys_ctrl = int.from_bytes(sys_ctrl, 'little')
    sys_ctrl |= (1 << 8)  # Set bit 8 for receiving mode
    write_subregister(0x2D,0x06,0x8000,18,2)
    write_register(0x0D, sys_ctrl.to_bytes(4, 'little'))

def get_rx_timestamp():
    """
    Retrieve timestamp of received signal
    :return: timestamp (int)
    
    """
    rx_ts = read_subregister(0x15,0x00,14,5)
    return int.from_bytes(rx_ts,'little')

def get_rx_quality():
    """
    Retreive quality indicators of received signal
    :return: point 2 amplitude (m) and signal noise (dB)
    
    """
    fp_amp2_bytes = read_subregister(0x12,0x02,8,2)
    fp_amp2 = int.from_bytes(fp_amp2_bytes,'little')

    std_noise_bytes = read_subregister(0x12,0x00,8,1)
    std_noise = int.from_bytes(std_noise_bytes,'little')

    return fp_amp2/std_noise

def get_tx_timestamp():
    """
    Retrieve timestamp of transmitted signal
    :return: timestamp (int)
    
    """
    tx_ts = read_subregister(0x17,0x00,14,5)
    return int.from_bytes(tx_ts,'little')

def init_ack_timing(w4r_time=None, ack_time=None):
    if w4r_time:
        write_register(0x1A, w4r_time.to_bytes(4,'little'))
    if ack_time:
        write_subregister(0x1A,0x03, ack_time,4,1)

def init_rx_timeout(wait_time):
    """
    Function to set the receive frame wait timeout period in the DWM1000

    :param wait_time: time in microseconds to wait for a response

    """
    write_subregister(0x0C,0,wait_time,4,2)

def bytes_to_int(b, byteorder='big'):
    n = 0
    if byteorder == 'big':
        for byte in b:
            n = (n << 8) | byte
    elif byteorder == 'little':
        reversed_result = []
        for i in range(len(b) - 1, -1, -1):
            reversed_result.append(b[i])
        result = reversed_result
        for byte in reversed_result:
            n = (n << 8) | byte
    else:
        raise ValueError("byteorder must be either 'big' or 'little'")
    return n

def int_to_bytes(n, byteorder='big'):
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

def set_send_interrupt():
    """
    sets DWM1000 to interrupt Pico once a message is successfully sent
    
    """
    write_register(0x0E, b'\x80\x00\x00\x00')

def set_receive_interrupt():
    """
    sets DWM1000 to interrupt Pico once a message is successfully received
    
    """
    write_register(0x0E, b'\x00\x40\x10\x00')

def toggle_buffer():
    status_register = read_register(0x0F,5)
    hsrbp = read_bit(status_register,30)
    icrbp = read_bit(status_register,31)
    rxovrr = read_bit(status_register,20)

    if rxovrr == 1:
        print("receiver overrun")
    if hsrbp != icrbp:
        system_control = read_register(0x0D,4)
        system_control = write_bit(system_control,24,1)
        write_register(0x0D,system_control)
    elif hsrbp == icrbp:
        clear_status_bits(0x0F,[15,14,13,10] )

def enable_double_buffering():
    system_config = read_register(0x04,4)
    system_config = write_bit(system_config,29,1) #init rxautr (re-enables radio if RX error or received message)
    system_config = write_bit(system_config,12,0)# init double buffer
    write_register(0x04,system_config)

