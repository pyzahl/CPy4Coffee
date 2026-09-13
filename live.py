import re
import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

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

# Initialize static history line objects once
line_tboiler, = ax_graph_t.plot([], [], label="Boiler", color="#ff3b30", linewidth=1.5)
line_tbrew,   = ax_graph_t.plot([], [], label="Brew", color="darkorange", linewidth=1.5)
line_pressure, = ax_graph_p.plot([], [], label="Pressure", color="#007aff", linewidth=1.5)


ax_graph_t.set_xlabel("Time (min)")
ax_graph_t.set_ylabel("Temperature (°C)")
ax_graph_t.set_title("Boiler and Brew Temperature Over Time")
ax_graph_t.legend()
ax_graph_t.grid(True)

ax_graph_p.set_xlabel("Time (min)")
ax_graph_p.set_ylabel("Brew Pressue (bar)")
ax_graph_p.set_title("Brew Pressure Over Time")
ax_graph_p.legend()
ax_graph_p.grid(True)


# Buffers
data_time, data_tbrew, data_tboiler, data_pressure = [], [], [], []


# --- STYLE THE DIALS ---
def style_gauge(ax, title, max_val, unit, ticks):
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
    
    # Text labels in the center of the gauge
    ax.text(0, -0.2, title, color='#aaaaaa', fontsize=12, ha='center', va='center', transform=ax.transAxes)
    val_text = ax.text(0.5, 0.3, f"0.0 {unit}", color='#ffffff', fontsize=20, ha='center', va='center', fontweight='black', transform=ax.transAxes)
    
    # Draw the analog needle path line object
    needle = ax.plot([0, 0], [0, 0.85], color='crimson', linewidth=3.5, zorder=5)[0]
    # Add a metallic pin cap in the center center circle pivot
    ax.scatter(0, 0, color='#cccccc', s=120, edgecolor='#000000', zorder=6)
    
    return needle, val_text

# Configure specific bounds and accents for your espresso metrics
needle_temp, text_temp = style_gauge(ax_temp, "BOILER TEMPERATURE", 140.0, "°C", [0, 20, 40, 60, 80, 100, 110, 114, 120, 140])
needle_press, text_press = style_gauge(ax_press, "EXTRACTION PRESSURE", 12.0, "bar", [0, 2, 4, 6, 7, 8, 9, 10, 11, 12])

# Recolor the needles for quick visual tracking
needle_temp.set_color('#ff3b30')  # Red alert for hot boiler
needle_press.set_color('#007aff') # Deep blue for extraction pressure water

# --- LIVE REFRESH DATA PIPELINE ---
def update_gauges(frame):
    # Continuously parse any incoming text hanging in the system serial buffer
    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            nums = regex.findall(line)

            print (line)
            
            # Match the 11 logging values from your newer log output format
            if len(nums) == 11:
                current_time        = float(nums[0]) # t in sec
                current_boiler_temp = float(nums[1])
                current_pressure    = float(nums[9])
                current_brew_temp   = float(nums[8]) # Brew Temp

                data_time.append (current_time)
                data_tboiler.append (current_boiler_temp)
                data_tbrew.append (current_brew_temp)
                data_pressure.append (current_pressure)

                if len(data_time) > 300:
                    data_time.pop(0)
                    data_tboiler.pop(0)
                    data_tbrew.pop(0)
                    data_pressure.pop(0)

                
                # --- CALCULATE NEEDLE ANGLES ---
                # Normalize metrics proportionally against maximum gauge values
                pct_temp = np.clip(current_boiler_temp / 140.0, 0.0, 1.0)
                angle_temp = MIN_RAD + (pct_temp * TOTAL_RAD_SWEEP)
                
                pct_press = np.clip(current_pressure / 12.0, 0.0, 1.0)
                angle_press = MIN_RAD + (pct_press * TOTAL_RAD_SWEEP)
                
                # --- UPDATE ANIMATION GRAPH LAYER ---
                # Point needle arrays to new radial angles [theta, radius_length]
                needle_temp.set_data([angle_temp, angle_temp], [0, 0.85])
                needle_press.set_data([angle_press, angle_press], [0, 0.85])
                
                # Update digital reading displays
                text_temp.set_text(f"{current_boiler_temp:.1f} °C")
                text_press.set_text(f"{current_pressure:.2f} bar")

                line_tboiler.set_data(data_time, data_tboiler)
                line_tbrew.set_data(data_time, data_tbrew)
                line_pressure.set_data(data_time, data_pressure)

                ax_graph_t.set_xrange (data_time[0], data_time[-1])
                ax_graph_t.set_yrange (0, 120)
                ax_graph_p.set_xrange (data_time[0], data_time[-1])
                ax_graph_p.set_yrange (0, 12)
                
        except Exception as e:
            # Prevent minor string formatting glitches from crashing the telemetry loop
            pass
            
    return needle_temp, needle_press, text_temp, text_press, line_tboiler, line_tbrew, line_pressure, ax_graph_t, ax_graph_p

# Initialize the 40ms frame handler loop (roughly 25fps fluid needle performance)
ani = FuncAnimation(fig, update_gauges, interval=40, blit=True, cache_frame_data=False)
plt.tight_layout()
plt.show()

# Safely close serial handle on plot window closure
ser.close()
