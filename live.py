import re
import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import savgol_filter
from scipy.signal import savgol_coeffs

import logging

# Configure the logger to save to a file
logging.basicConfig(
    filename='live-app.log', 
    filemode='a', # 'a' appends data; change to 'w' to overwrite every run
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Write log messages
logging.info('Start Log: live-app.log')
#logging.warning('This is a warning log!')

# --- CONFIGURATION ---
# Replace with your actual macOS device name from `ls /dev/cu.*`
SERIAL_PORT = '/dev/cu.usbmodemCCD82AB862271'  # Example ESP32 port path
BAUD_RATE = 115200

# Regular expression to catch the 11 floating numbers from your CPy4Coffee output
regex = re.compile(r"[-+]?\d*\.\d+|\d+")

# --- SERIAL CONNECTION INITIALIZATION ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
except Exception as e:
    print(f"Error opening serial port {SERIAL_PORT}: {e}")
    print("Please check your port name and ensure the ESP32 is connected.")
    exit()

# --- MATPLOTLIB GAUGE SETUP (Using Polar Projections) ---
fig = plt.figure(figsize=(11, 5.5), facecolor='#121212')

# Define angular sweep boundaries for a classic 270-degree dashboard arc
# Matplotlib polar angles are in radians: 0 is Right, pi/2 is Up, pi is Left...
MIN_RAD = -np.pi / 4       # Bottom Right
MAX_RAD = 5 * np.pi / 4    # Bottom Left
TOTAL_RAD_SWEEP = MAX_RAD - MIN_RAD

# Gauge Subplot 1: Temperature (0°C to 140°C)
ax_temp = fig.add_subplot(221, polar=True, facecolor='#1e1e1e')
ax_temp.set_thetalim(MIN_RAD, MAX_RAD)

# Gauge Subplot 2: Pressure (0 to 12 Bar)
ax_press = fig.add_subplot(222, polar=True, facecolor='#1e1e1e')
ax_press.set_thetalim(MIN_RAD, MAX_RAD)

# History Graph Subplot 3: Temp, Pressure (0 to 12 Bar)
ax_graph_t = fig.add_subplot(223, facecolor='#1e1e1e')
ax_graph_p = fig.add_subplot(224, facecolor='#1e1e1e')

ax_graph_t.tick_params(axis='both', colors='#ffffff', labelsize=10)
ax_graph_p.tick_params(axis='both', colors='#ffffff', labelsize=10)


ax_graph_t.set_xlabel("Time in s", color='#ffffff')
ax_graph_t.set_ylabel("Temperature in °C", color='#ffffff')
#ax_graph_t.set_title("Boiler and Brew Temperature Over Time", color='#ffffff')
ax_graph_t.legend()
ax_graph_t.grid(True)

ax_graph_p.set_xlabel("Time in s", color='#ffffff')
ax_graph_p.set_ylabel("Brew Pressue in bar", color='#ffffff')
#ax_graph_p.set_title("Brew Pressure Over Time", color='#ffffff')
ax_graph_p.legend()
ax_graph_p.grid(True)


# Initialize static history line objects once
line_tboiler, = ax_graph_t.plot([], [], label="Boiler", color="#ff3b30", linewidth=1.5)
line_tbrew,   = ax_graph_t.plot([], [], label="Brew", color="darkorange", linewidth=1.5)
line_pressure, = ax_graph_p.plot([], [], label="Pressure", color="#007aff", linewidth=1.5)



# Buffers
data_time, data_tbrew, data_tboiler, data_pressure = [], [], [], []

tboiler_set_point = 114

# --- STYLE THE DIALS ---
def style_gauge(ax, title, max_val, unit, ticks, second_hand=False):
    ax.set_theta_direction(-1) # Clockwise sweep rotation
    ax.set_theta_zero_location('W') # Start tracking angles relative to West/Left

    # Map raw value scales to the physical angular degrees of the circular slice
    tick_positions = [MIN_RAD + (t / max_val) * TOTAL_RAD_SWEEP for t in ticks]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([f"{t}" for t in ticks], color='#ffffff', fontsize=11, fontweight='bold')
    
    # Hide the interior radius lines/labels to keep it clean like an analog gauge
    ax.set_yticklabels([])
    ax.grid(True, color='#444444', linestyle=':')
    ax.spines['polar'].set_color('#666666')
    ax.spines['polar'].set_linewidth(2)

    rmax = ax.get_rmax()
    stub_length = 0.05 * rmax  # Length of the stub (5% of max radius)
    for angle in tick_positions:
        # Plot a line from the outer rim (rmax) extending outwards (rmax + stub_length)
        ax.plot([angle, angle], [rmax, rmax + stub_length], 
                color='#ffffff', linewidth=2.5, clip_on=False)

    # Set Point Marker (Boiler hack)
    if second_hand:
        angle = MIN_RAD + (tboiler_set_point / max_val) * TOTAL_RAD_SWEEP
        setpt = ax.plot([angle, angle], [rmax - stub_length, rmax + stub_length], color='yellow', linewidth=4, clip_on=False)[0]
        theta_start = MIN_RAD + (75 / max_val) * TOTAL_RAD_SWEEP
        theta_end   = MIN_RAD + (85 / max_val) * TOTAL_RAD_SWEEP
        
        theta_range = np.linspace(theta_start, theta_end, 100)
        ax.fill_between(
            theta_range, 
            0.5*rmax, 
            rmax, 
            color='#80ee80',      # Light pastel blue/gray color
            alpha=0.6,            # Semi-transparent so gridlines stay visible
            zorder=0              # Puts the background color BEHIND your data lines
        )
    else:
        theta_start = MIN_RAD + (6 / max_val) * TOTAL_RAD_SWEEP
        theta_end   = MIN_RAD + (8 / max_val) * TOTAL_RAD_SWEEP
        
        theta_range = np.linspace(theta_start, theta_end, 100)
        ax.fill_between(
            theta_range, 
            0.5*rmax, 
            rmax, 
            color='#80ee80',      # Light pastel blue/gray color
            alpha=0.6,            # Semi-transparent so gridlines stay visible
            zorder=0              # Puts the background color BEHIND your data lines
        )
        
    
    # Text labels in the center of the gauge
    ax.text(0.5, -0.2, title, color='#aaaaaa', fontsize=12, ha='center', va='center', transform=ax.transAxes)
    val_text = ax.text(0.5, 0.3, f"0.0 {unit}", color='#ffffff', fontsize=20, ha='center', va='center', fontweight='black', transform=ax.transAxes)
    if second_hand:
        val2_text = ax.text(0.5, 0.15, f"0.0 {unit}", color='#ffffff', fontsize=20, ha='center', va='center', fontweight='black', transform=ax.transAxes)
    
    # Draw the analog needle path line object
    needle = ax.plot([0, 0], [0, 0.85], color='crimson', linewidth=3.5, zorder=5)[0]
    if second_hand:
        # Draw the analog needle path line object
        needle2 = ax.plot([0, 0], [0, 0.85], color='crimson', linewidth=3.5, zorder=5)[0]

    # Add a metallic pin cap in the center center circle pivot
    ax.scatter(0, 0, color='#cccccc', s=120, edgecolor='#000000', zorder=6)
    
    if second_hand:
        return needle, needle2, val_text, val2_text, setpt
    else:
        return needle, val_text

# Configure specific bounds and accents for your espresso metrics
needle_temp, needle2_temp, text_temp, text2_temp, setpt = style_gauge(ax_temp, "BOILER & BREW TEMPERATURES", 140.0, "°C", [0, 20, 40, 60, 80, 100, 110, 120, 140, tboiler_set_point], True)
needle_press, text_press = style_gauge(ax_press, "EXTRACTION PRESSURE", 12.0, "bar", [-1, 0, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12])

# Recolor the needles for quick visual tracking
needle_temp.set_color('#ff3b30')  # Red alert for hot boiler
needle2_temp.set_color('#ff6b60')  # Orange for brew head
needle_press.set_color('#007aff') # Deep blue for extraction pressure water


window_length = 11
polyorder = 2

# 'pos=window_length-1' means we are smoothing the very last point 
# using only the past points (no future data)
coeffs = savgol_coeffs(window_length, polyorder, pos=window_length-1)
#print (coeffs)

# --- LIVE REFRESH DATA PIPELINE ---
def update_gauges(frame):
    # Continuously parse any incoming text hanging in the system serial buffer
    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            nums = regex.findall(line)

            print (line)
            logging.info(line)
            
            # Match the 11 logging values from your newer log output format
            if len(nums) == 11:
                current_time        = float(nums[0]) # t in sec
                current_boiler_temp = float(nums[1])
                current_pressure    = float(nums[9])
                current_brew_temp   = float(nums[8]) # Brew Temp

                tboiler_set_point   = float(nums[2]) # Set Point 

                data_time.append (current_time)
                data_tboiler.append (current_boiler_temp)
                data_tbrew.append (current_brew_temp)
                data_pressure.append (current_pressure)
                
                if len(data_time) > 1000:
                    data_time.pop(0)
                    data_tboiler.pop(0)
                    data_tbrew.pop(0)
                    data_pressure.pop(0)

                if len(data_time) > window_length:
                    # Fast dot product to get the latest smoothed point
                    current_boiler_temp = np.dot(np.array(data_tboiler[-window_length:]), coeffs)
                    current_brew_temp   = np.dot(np.array(data_tbrew[-window_length:]), coeffs)
                    
                # --- CALCULATE NEEDLE ANGLES ---
                # Normalize metrics proportionally against maximum gauge values
                pct_temp = np.clip(current_boiler_temp / 140.0, 0.0, 1.0)
                angle_temp = MIN_RAD + (pct_temp * TOTAL_RAD_SWEEP)

                pct_tempbrew = np.clip(current_brew_temp / 140.0, 0.0, 1.0)
                angle_tempbrew = MIN_RAD + (pct_tempbrew * TOTAL_RAD_SWEEP)

                
                pct_press = np.clip(current_pressure / 12.0, 0.0, 1.0)
                angle_press = MIN_RAD + (pct_press * TOTAL_RAD_SWEEP)
                
                # --- UPDATE ANIMATION GRAPH LAYER ---
                # Point needle arrays to new radial angles [theta, radius_length]
                needle_temp.set_data([angle_temp, angle_temp], [0, 0.85])
                needle2_temp.set_data([angle_tempbrew, angle_tempbrew], [0, 0.85])

                rmax = 1. #ax_graph_t.get_rmax()
                stub_length = 0.05 * rmax  # Length of the stub (5% of max radius)
                angle = MIN_RAD + (tboiler_set_point / 140.0) * TOTAL_RAD_SWEEP
                setpt.set_data([angle, angle], [rmax - stub_length, rmax + stub_length])
                
                needle_press.set_data([angle_press, angle_press], [0, 0.85])
                
                # Update digital reading displays
                text_temp.set_text(f"{current_boiler_temp:.1f} °C")
                text2_temp.set_text(f"{current_brew_temp:.1f} °C")
                text_press.set_text(f"{current_pressure:.2f} bar")

                t = np.array(data_time) - data_time[0]
                if len(data_time) > 2:

                    line_tboiler.set_data(t, data_tboiler)
                    line_tbrew.set_data(t, data_tbrew)
                    line_pressure.set_data(t, data_pressure)
                    
                    ax_graph_t.set_xlim (t[0], t[-1])
                    ax_graph_t.set_ylim (0, 120)
                    ax_graph_p.set_xlim (t[0], t[-1])
                    ax_graph_p.set_ylim (0, 12)



                    
        except Exception as e:
            # Prevent minor string formatting glitches from crashing the telemetry loop
            pass
            
    return needle_temp, needle2_temp, needle_press, text_temp, text2_temp, text_press, line_tboiler, line_tbrew, line_pressure

# Initialize the 40ms frame handler loop (roughly 25fps fluid needle performance)
ani = FuncAnimation(fig, update_gauges, interval=40, blit=False, cache_frame_data=False)
plt.tight_layout()
plt.show()

# Safely close serial handle on plot window closure
ser.close()
