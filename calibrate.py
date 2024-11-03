from machine import Pin
import time
from node import UWBNode
import uasyncio

led = Pin("LED", Pin.OUT)
irq_pin = Pin(14, Pin.IN)  # Assuming the IRQ pin is connected to GPIO 14

# Example usage
PAN_ID = 0xB34A  # Example PAN ID
SRC_ADDR = 0x1234 #update for src

DISTANCE = 7.94 #m
SPEED_OF_LIGHT = 299702547 #m/s
UNIT_CONVERSION = 1.565*(10**-11) #s

calibration_data = {
    "t1": [],
    "t2": [],
    "delay": []
                    }

def remove_outliers(data):
    # Sort the data
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    # Calculate Q1, Q3, and IQR
    q1_index = n // 4
    q3_index = 3 * n // 4
    q1 = sorted_data[q1_index]
    q3 = sorted_data[q3_index]
    iqr = q3 - q1
    
    # Define bounds
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    # Remove outliers
    return [x for x in data if lower_bound <= x <= upper_bound]


async def main():
    device = UWBNode(PAN_ID,SRC_ADDR)
    await device.init()
    print("searching")

    while len(calibration_data["t1"]) <= 100:
        # Perform TWR and transmit our own message
        isResponse = await device.twr_response()
        if isResponse == True:
            t1, t2 = await device.get_calibration_data()
            calibration_data["t1"].append(t1)
            calibration_data["t2"].append(t2)

        await uasyncio.sleep_ms(50)
    
    tSum = 0
    for i in range(len(calibration_data["t1"])):
        td = calibration_data["t1"][i] - calibration_data["t2"][i] - ((2*DISTANCE)/(UNIT_CONVERSION*SPEED_OF_LIGHT))
        calibration_data["delay"].append(td)

    new_data = remove_outliers(calibration_data["delay"])

    for d in new_data:
        tSum+=d
  
    t_delay = tSum/len(new_data)

    print(f"antenna delay: {t_delay}")

uasyncio.run(main())