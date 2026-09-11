# boot.py
import board
import digitalio
import storage

# 1. Set up pin D1 (using internal pull-up)
btn_d1 = digitalio.DigitalInOut(board.D1)
btn_d1.switch_to_input(pull=digitalio.Pull.DOWN)

# 2. Set up pin D2 (using internal pull-up)
btn_d2 = digitalio.DigitalInOut(board.D2)
btn_d2.switch_to_input(pull=digitalio.Pull.DOWN)

# 3. Read buttons (True = not pressed, False = pressed/grounded)
# If BOTH buttons are held down at boot:
if btn_d1.value and btn_d2.value:
  # Writable by COMPUTER (Default mode). Your code.py CANNOT write to it.
  storage.remount("/", readonly=True)
  print("USB Mode: Computer can write (Read-only to Python script)")
else:
  # Writable by CODE. Your Python script can write JSON/text files.
  storage.remount("/", readonly=False)
  print("Data Mode: Python script can write (Read-only to Computer)")

# Clean up pins to free them for code.py
btn_d1.deinit()
btn_d2.deinit()
