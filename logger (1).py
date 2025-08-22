import serial
import csv
import time
import os

# Auto-detect COM port (change if needed)
PORT = "COM7"   # update if your ESP32 is on a different port
BAUD = 115200

arduino = serial.Serial(port=PORT, baudrate=BAUD, timeout=1)

csv_file = "data.csv"
command_file = "command.txt"

# Create CSV with correct headers if not exists
if not os.path.exists(csv_file):
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "soil", "temperature", "humidity"])

print("Logger started... Press CTRL+C to stop.")

while True:
    try:
        line = arduino.readline().decode(errors="ignore").strip()
        if line and "," in line:
            parts = line.split(",")
            if len(parts) == 3:
                soil, temp, hum = parts
                with open(csv_file, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([time.time(), soil, temp, hum])
                print("Logged:", soil, temp, hum)

        # Check for pump command
        if os.path.exists(command_file):
            with open(command_file, "r") as f:
                cmd = f.read().strip()
            if cmd in ["ON", "OFF"]:
                arduino.write((cmd + "\n").encode())
                print("Sent command:", cmd)
            open(command_file, "w").close()  # clear after sending

    except Exception as e:
        print("Error:", e)
        time.sleep(1)
