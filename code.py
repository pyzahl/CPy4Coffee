import os
import json

import board
import analogio
import digitalio

#import adafruit_thermistor
import time
import displayio
from adafruit_display_text import label
from adafruit_progressbar.horizontalprogressbar import (
    HorizontalProgressBar,
    HorizontalFillDirection,
)
from terminalio import FONT

### S3 only BLE
#from adafruit_ble import BLERadio
#from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
#from adafruit_ble.services.nordic import UARTService

# --- CONFIGURATION CONSTANTS ---
TARGET_TEMP       = 114.0    # default (if no settings) Target boiler temperature in Celsius ~0.7bar (1.66 bar abs)
TARGET_TEMP_MAX   = 125.0    # max cut off/limit
TARGET_TEMP_MIN   = 0. # 60.0
TARGET_TEMP_RESET = 114.0    # default (after reset) Target boiler temperature in Celsius ~0.7bar (1.66 bar abs)

CP = 0.3
CI = CP*0.001
CD = CP*10.
LPmu = 0.025
LP1mu = 1.0-LPmu

CYCLE_TIME = 0.25
B_COEFFICIENT = 3950     # Thermistor Beta coefficient (check your datasheet)
SERIES_RESISTOR = 10000  # 10k ohm series resistor
THERMISTOR_NOMINAL = 10000 # 10k ohm resistance at 25C
TEMP_NOMINAL = 25.0      # 25 degrees Celsius

MAX_LENGTH = 200

#ble = BLERadio()
#uart_server = UARTService()
#advertisement = ProvideServicesAdvertisement(uart_server)


# 2. Setup Display Group (Compatible with CircuitPython 10.x+)
# For older firmware (pre-v8.0), replace 'display.root_group' with 'display.show(splash)'
display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

# set progress bar width and height relative to board's display
width  = board.DISPLAY.width - 32
height = 30

xl = 0
xv = 30
yo = 15
x = yo-5+board.DISPLAY.width // 2 - width // 2
y = 0 #board.DISPLAY.height // 3

# create Pressure bar object at (x, y)
pressure_bar = HorizontalProgressBar(
    (x, y), (width, height),
    min_value=0.0, 
    max_value=20.0, 
    bar_color=0x99AA00,       # Green filled bar
    outline_color=0xFFFFFF,   # White border
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)

# Append progress_bar to the splash group
splash.append(pressure_bar)
pressure_label = label.Label(FONT, text="p", color=0xFFFFFF, x=xl, y=y+yo)
pressure_label.scale = 2  # Double the font size for readability
splash.append(pressure_label)

pressure_value = label.Label(FONT, text="-.-- bar", color=0xFFFFFF, x=xv, y=y+yo)
pressure_value.scale = 3  # Large crisp layout for the numbers
splash.append(pressure_value)


y=35
# create Temp-bar object at (x, y)
Tboiler_bar = HorizontalProgressBar(
    (x, y), (width, height),
    min_value=0.0, 
    max_value=125.0, 
    bar_color=0x00AA00,       # Green filled bar
    outline_color=0xFFFFFF,   # White border
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)

# Append progress_bar to the splash group
splash.append(Tboiler_bar)
Tboiler_label = label.Label(FONT, text="Tb", color=0xFFFFFF, x=xl, y=y+yo)
Tboiler_label.scale = 2  # Double the font size for readability
splash.append(Tboiler_label)

Tboiler_value = label.Label(FONT, text="---.-/--- C", color=0xFFFFFF, x=xv, y=y+yo)
Tboiler_value.scale = 3  # Large crisp layout for the numbers
splash.append(Tboiler_value)

y=65
# SetPoint
# create Temp-bar object at (x, y)
TboilerS_bar = HorizontalProgressBar(
    (x, y), (width, 15),
    min_value=0.0, 
    max_value=125.0, 
    bar_color=0xFFFF00,       # Green filled bar
    outline_color=0xFFFFFF,   # White border
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)
splash.append(TboilerS_bar)

y=72
# HeatingPwr
# create Temp-bar object at (x, y)
TboilerPWR_bar = HorizontalProgressBar(
    (x, y), (width, 10),
    min_value=0.0, 
    max_value=1.0, 
    bar_color=0xFF0000,       # Green filled bar
    outline_color=0xFFFFFF,   # White border
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)
splash.append(TboilerPWR_bar)

H_label = label.Label(FONT, text="Ht", color=0xFFFFFF, x=xl, y=y+5)
H_label.scale = 1  # Double the font size for readability
splash.append(H_label)



y=83
# HeatingPwrI
# create Temp-bar object at (x, y)
TboilerPWRI_bar = HorizontalProgressBar(
    (x, y), (width, 10),
    min_value=-1.0, 
    max_value=1.0, 
    bar_color=0xFF7000,       # Green filled bar
    outline_color=0xFFFFFF,   # White border
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)
splash.append(TboilerPWRI_bar)

HI_label = label.Label(FONT, text="Hi", color=0xFFFFFF, x=xl, y=y+5)
HI_label.scale = 1  # Double the font size for readability
splash.append(HI_label)

y=94
# HeatingPwrD
# create Temp-bar object at (x, y)
TboilerPWRD_bar = HorizontalProgressBar(
    (x, y), (width, 10),
    min_value=-1.0, 
    max_value=1.0, 
    bar_color=0xFF7070,       # Green filled bar
    outline_color=0xFFFFFF,   # White border
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)
splash.append(TboilerPWRD_bar)

HD_label = label.Label(FONT, text="Hd", color=0xFFFFFF, x=xl, y=y+5)
HD_label.scale = 1  # Double the font size for readability
splash.append(HD_label)


y=105
# create Temp-bar object at (x, y)
Tbrew_bar = HorizontalProgressBar(
    (x, y), (width, height),
    min_value=0.0, 
    max_value=125.0, 
    bar_color=0xAAAA00,       # Green filled bar
    outline_color=0xFFFFFF,   # White border
    direction=HorizontalFillDirection.LEFT_TO_RIGHT,
)

# Append progress_bar to the splash group
splash.append(Tbrew_bar)
Tbrew_label = label.Label(FONT, text="Tp", color=0xFFFFFF, x=xl, y=y+yo)
Tbrew_label.scale = 2  # Double the font size for readability
splash.append(Tbrew_label)

Tbrew_value = label.Label(FONT, text="---.- C", color=0xFFFFFF, x=xv, y=y+yo)
Tbrew_value.scale = 3  # Large crisp layout for the numbers
splash.append(Tbrew_value)

# Sensors

thermistorBoiler = analogio.AnalogIn(board.A2)  ## 3V3 -- R10k -- A1 -- TH -- GND
thermistorBrew   = analogio.AnalogIn(board.A3)  ## 3V3 -- R10k -- A2 -- TH -- GND
pressurePiston   = analogio.AnalogIn(board.A4)  ## GND -- R10k -- A3 -- R6k2 -- PrTransducer Signal, 5V (VBUS), GND

# Set Pt Ctrl Buttons
set_up = digitalio.DigitalInOut(board.BUTTON)
set_up.switch_to_input(pull=digitalio.Pull.UP)

set_dn = digitalio.DigitalInOut(board.D1)
set_dn.switch_to_input(pull=digitalio.Pull.DOWN)

set_r  = digitalio.DigitalInOut(board.D2)
set_r.switch_to_input(pull=digitalio.Pull.DOWN)

# MOSFET / SSR Control (Digital Output)
ssr = digitalio.DigitalInOut(board.D13)
ssr.direction = digitalio.Direction.OUTPUT
ssr.value = False  # Start OFF for safety

file_path = "/settings.json"

config_data = { 'TempSetPoint': TARGET_TEMP, 'data_time': [], 'data_tboiler': [], 'data_pwr': [], 'data_tbrew': [], 'data_pressure': [] }

# STORE: Save the array to the flash drive as JSON
def save_settings(data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f)
            print("Array successfully stored to flash!")
    except OSError as e:
        print("Failed to write to flash. Is the drive write-protected?", e)

# RESTORE: Load the array back from the flash drive
def load_settings(default):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            print("Array successfully restored from flash:", data)
        return data
    except (OSError, ValueError):
        print("No settings file found or file corrupted. Returning default.")
        try:
            with open(file_path, "r") as f:
                print("Creating Default.")
                json.dump(default, f)
        except (OSError, ValueError):
            print("Drive Read Only. Default Always")
        return default


def get_temperature(pin):
    """Calculates temperature using the Steinhart-Hart equation."""

    samples = 64
    total = 0
    for _ in range(samples):
        total += pin.value
    reading = total // samples
    
    voltage = (reading * 3.3) / 65535
    if voltage >= 3.3 or voltage <= 0:
        return 0.0 # Prevent division by zero
    
    resistance = SERIES_RESISTOR / ((3.3 / voltage) - 1.0)
    
    steinhart = resistance / THERMISTOR_NOMINAL      # (R/Ro)
    steinhart = __import__('math').log(steinhart)    # ln(R/Ro)
    steinhart /= B_COEFFICIENT                        # 1/B * ln(R/Ro)
    steinhart += 1.0 / (TEMP_NOMINAL + 273.15)       # + (1/To)
    steinhart = 1.0 / steinhart                      # Invert
    steinhart -= 273.15                              # Convert to Celsius
    return steinhart


# Resistor values in ohms
R1 = 6200.0
R2 = 10000.0

# Divider scaling factor: V_in = V_pin * ((R1 + R2) / R2)
DIVIDER_RATIO = (R1 + R2) / R2  # 1.62

def read_Psensor(pin):
    # ESP32-S2 calibrated scaling factor
    v_pin = (pin.value * 2.57) / 51000.0 * 0.491/0.42 ## * Reading Calibration
    #v_pin = (pin.value * 3.3) / 65535
    
    # Scale back to original 0-5V sensor range
    v_sensor = v_pin * DIVIDER_RATIO

    # Map 0.5V - 4.5V sensor output to 0 - 20 bar
    if v_sensor < 0.5:
        return 0.0, v_sensor
    
    pressure_bar = ((v_sensor - 0.5) * 20.0) / (4.5 - 0.5)
    return max(0.0, pressure_bar), v_sensor


### START MAIN LOOP HERE

config_data = load_settings (config_data)
t0 = time.monotonic()
t  = time.monotonic()
ts = 0.0
PwrI = 0.
PwdD = 0.
Tboiler=get_temperature(thermistorBoiler)
temp_control_lp = Tboiler
temp_control_lp_prev = Tboiler

while True:

    
    # Advertise when not connected.
    #ble.start_advertising(advertisement)
    #while not ble.connected:
    #    pass
    #ble.stop_advertising()

    #while ble.connected:
    try:
        t  = time.monotonic()
        Tboiler=get_temperature(thermistorBoiler)
        Tbrew=get_temperature(thermistorBrew)
        Pbrew, V = read_Psensor(pressurePiston)

        temp_control = Tboiler
        temp_control_lp = LP1mu*temp_control_lp + LPmu*temp_control
        temp_gradient = temp_control_lp - temp_control_lp_prev;
        temp_control_lp_prev = temp_control_lp
        
        # --- PID CONTROLLER ---

        err = config_data['TempSetPoint'] - temp_control

        Pwr = CP*err ## Proportional Part

        if abs(err) < 10.:
            PwrI += CI*err
        else:
            PwrI = 0.

        PwrD = -CD*temp_gradient
            
        PwrI = max(-1., min(PwrI, 1.))

        PwrNorm = Pwr + PwrI + PwrD

        PwrNorm = max(0., min(PwrNorm, 1.))
        
        if err < -0.1: # instant power cut-off
            PwrNorm = 0.
        
        
        # --- BOILER TEMPERATURE CONTROL LOGIC ---
            
        print(f"{t:8.1f} s | Boiler: {Tboiler:5.1f}°C [Set: {config_data['TempSetPoint']:5.1f}°C ] | SSR: H{PwrNorm:4.2f} | Err: {err:5.1f} °C |  PP: {Pwr:5.2f} | PD: {PwrD:5.2f}  | PI: {PwrI:5.2f} | Brew: {Tbrew:5.1f}°C | {Pbrew:5.2f} bar [{V:.3f} V]")

        #uart_server.write('{},{},{}\n'.format(Tboiler,Tbrew,Pbrew))
        
        # Update display
        pressure_bar.value = Pbrew
        Tboiler_bar.value = Tboiler
        TboilerS_bar.value = config_data['TempSetPoint']
        TboilerPWR_bar.value = PwrNorm
        TboilerPWRI_bar.value = PwrI
        TboilerPWRD_bar.value = PwrD
        Tbrew_bar.value = Tbrew
        pressure_value.text = f"{Pbrew:.2f} bar"
        Tboiler_value.text = f"{Tboiler:.1f}/{config_data['TempSetPoint']:.0f} C" #"°C"
        Tbrew_value.text = f"{Tbrew:.1f} C"

        if not set_up.value and config_data['TempSetPoint'] < TARGET_TEMP_MAX:
            config_data['TempSetPoint'] += 1
            
        if set_dn.value and config_data['TempSetPoint'] > TARGET_TEMP_MIN:
            config_data['TempSetPoint'] -= 1
            
        if set_r.value:
            config_data['TempSetPoint'] = TARGET_TEMP_RESET
        
        # --- SAFETY OVERRIDE ---
        # Hard limits to prevent physical damage if pressure gets too high
        if Pbrew > 15.0 or Tboiler > 125.0 or Tbrew > 100:
            ssr.value = False
            PwrNorm = 0.0
            print("⚠️ SAFETY OVERRIDE TRIGGERED: Pressure or Temp too high!")

        ## PWM heating mode
        t_on  = CYCLE_TIME*PwrNorm
        t_off = CYCLE_TIME-t_on
        if PwrNorm > 0:
            ssr.value = True
        else:
            ssr.value = False
        time.sleep(t_on)

        if PwrNorm < 1.0:
            ssr.value = False  # Too hot! Turn off heating element
            time.sleep(t_off)

        t += CYCLE_TIME ## + eps processing ??

        if Pbrew > 0.1:
            if len(config_data['data_time']) > MAX_LENGTH:
                config_data['data_time'].pop(0)
                config_data['data_tboiler'].pop(0)
                config_data['data_tbrew'].pop(0)
                config_data['data_pressure'].pop(0)
                config_data['data_pwr'].pop(0)

            config_data['data_time'].append(t)
            config_data['data_tboiler'].append(Tboiler)
            config_data['data_tbrew'].append(Tbrew)
            config_data['data_pressure'].append(Pbrew)
            config_data['data_pwr'].append(PwrNorm)
          
        if t > ts:
            TboilerS_bar.value = 125.0 # Flash
            save_settings (config_data)
            ts = t+30
            
    except Exception as e:
        ssr.value = False  # Failsafe: Turn off heater if code errors out
        print(f"Error in control loop: {e}")
        save_settings (config_data)

    
