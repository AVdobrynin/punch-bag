import sys
import re
from hx711_weight import HX711

pin_in = 0
pin_out = 0

def hx_init_start(hx):
        """
        Initializes and starts the HX711 sensor.

        Resets the sensor and sets the gain for channel A to 64. Then it zeroes the sensor by taking the mean of 10 readings and sets the tare value to the mean of 10 more readings. This is done to account for any offset in the sensor.

        :param hx: The HX711 sensor object
        :return: None
        """
        hx.reset()
        hx.set_gain_A(gain=64)  # You can change the gain for channel A  at any time.
        hx.select_channel(channel='A')  # Select desired channel. Either 'A' or 'B' at any time.
        data = hx.get_data_mean(readings=10)
        result = hx.zero(readings=10)
        data = hx.get_data_mean(readings=10)

def calibrate_hx(known_weight: float, hx: HX711):

    """
    Calibrates the HX711 sensor.

    This function takes the known weight in grams and the HX711 sensor object as arguments.
    It takes the mean of 30 readings from the sensor, and then calculates the ratio of the mean to the known weight.
    This ratio is then returned as the calibration factor.

    :param known_weight: the known weight in grams
    :param hx: the HX711 sensor object
    :return: the calibration factor
    """
    known_weight = known_weight * 1000
    data = hx.get_data_mean(readings=30)
    ratio = data / known_weight
    return ratio

def calibrate(hx):
    """
    Calibration tool for HX711 sensor.

    This function reads the input from the user and guides the user through the calibration process.
    It first asks the user to input the pins to connect the sensor to the device in the format xx,yy.
    Then it asks the user to input the known weight in kilogrammes.
    It then calculates the calibration factor and prints it to the user.
    The user can then choose to continue the calibration process by inputting new pins and weights, or exit the tool by typing 'Exit'.

    :param hx: the HX711 sensor object
    :return: None
    """
    print("enter pins to connect the sensor to the device in format xx,yy:")
    for line in sys.stdin:
        if  (re.match(r'(\d+),(\d+)', line)) and (pin_in == 0) and (pin_out == 0):
            print(f"Calibration pin set to {re.match(r'(\d+),(\d+)', line).group(1)} and {re.match(r'(\d+),(\d+)', line).group(2)}")
            print("initiate calibration")
            pin_in = re.match(r'(\d+),(\d+)', line).group(1)
            pin_out = re.match(r'(\d+),(\d+)', line).group(2)
            hx = HX711(pin_in, pin_out)
            hx_init_start(hx)
            print("initialization done")
            print(f'Put into sensor known weight and after send weight in kilogrammes to continue:')
        elif (re.match(r'(\d+),(\d+)', line)):
            print(f"Calibration weight set to {re.match(r'(\d+),(\d+)', line).group(1)}")
            print("Calibration started")
            ratio = calibrate_hx(float(re.match(r'(\d+),(\d+)', line).group(1)), hx)
            print(f"Calibration factor is {ratio}")
            print("enter pins to connect the sensor to the device in format xx,yy to continue or type 'Exit' to exit:")
        if 'Exit' == line.rstrip():
            break
    print("Calibration tool ended")


def main():
    hx = 0
    calibrate(hx)

if __name__ == "__main__":
    print("CALIBRATING TOOL STARTED")
    main()
