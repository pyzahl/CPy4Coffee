import re
import numpy as np
import matplotlib.pyplot as plt



# 1. Read and parse the file line by line
data_list = []
# Matches integers, decimals, and explicitly captures negative signs
regex = re.compile(r"[-+]?\d*\.\d+|\d+")

with open("LaPavoniTest3.log", "r") as file:
    for line in file:
        if line.strip():  # Skip empty lines
            numbers = regex.findall(line)
            if len(numbers) == 11:  # Adjusted to match the 11 metrics in the new format
                data_list.append([float(n) for n in numbers])

# 2. Convert to a 2D NumPy array
data = np.array(data_list)

# 3. Extract columns via slicing
time         = data[:, 0]/60
boiler_temp  = data[:, 1]
set_temp     = data[:, 2]
ssr_state    = data[:, 3]
error        = data[:, 4]
p_term       = data[:, 5]  # PP
d_term       = data[:, 6]  # PD
i_term       = data[:, 7]  # PI
brew_temp    = data[:, 8]
pressure     = data[:, 9]
voltage      = data[:, 10]


# 4. Example Matplotlib Setup
plt.figure(figsize=(10, 6))

# SSR PWM Power
plt.plot(time, ssr_state*100, label="SSR PWM Power (%)", alpha=0.3, color="purple")
plt.plot(time, p_term*100, label="P (%)", alpha=0.4,  color="blue")
plt.plot(time, i_term*100, label="I (%)", alpha=0.4,  color="olive")
plt.plot(time, d_term*100, label="D (%)", alpha=0.4,  color="darkgreen")
plt.plot(time, error, label="Temp Err (°C)", color="purple")

# Plot Temperatures
plt.plot(time, boiler_temp, label="Boiler Temp (°C)", color="crimson")
plt.plot(time, set_temp, label="Set Temp (°C)", color="darkred", linestyle="--")
plt.plot(time, brew_temp, label="Brew Temp (°C)", color="darkorange")



plt.xlabel("Time (min)")
plt.ylabel("Temperature (°C)")
plt.title("Boiler and Brew Temperature Over Time")
plt.legend()
plt.grid(True)

plt.show()
