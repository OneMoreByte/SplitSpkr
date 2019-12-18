#/usr/bin/env python3

import soundcard as sc
import soundfile as sf
import numpy as np
import serial
import threading
import glob

flipped = False
mic-data = []

# Runs as it's own thread. Reads the data from the accelerometer
def read_accel_data():
    ard = glob.glob("/dev/ttyACM*")
    if len(ard) == 0:
        print("No arduino! Killing thread. Flipping disabled!!!")
        exit()
    sr = serial.Serial(ard[0])
    state = "N"
    while True:
        data = sr.readline().decode("utf-8").strip().split()
        if data and len(data) == 3:
            x = int(data[0])
            y = int(data[1])
            z = int(data[2])
        if x == 0 and y == 0 and state != "F" and state == "N":
            if not flipped:
                flipped = not flipped
            state = "F" 
        elif x == 0 and y == 1 and state != "N":
            state = "N" 
    sr.reset_input_buffer()


def record_playback(device, length, sr):
    data = device.recorder(samplerate=sr).record(numframes=length)
    mx = 0.0
    for x in data[..., 0]:
        if x > mx:
            mx = x
    mic-data.append(mx)

def play_data(device, data, sr):
    with device.player(samplerate=sr) as sp:
        sp.play(data)


# Compares the loudness of two devices and allows user to set volume
def normalize_loudness(dev_l, dev_r):
    data, sr = load_file("./speaker-test.wav")
    col, row = data.shape
    peaks = [0, 0]
    devices = [dev_l, dev_r]
    mic = sc.default_microphone()
    
    for speaker in devices:
        t_mic = threading.Thread(target=record_playback, args=(mic, row, sr))
        t_spk = threading.Thread(target=play_data, args=(speaker, data, sr))
        t_mic.start()
        t_spk.start()
        t_mic.join()
    print(mic-data)
    return [dev_l, dev_r]

# Picks a device from availible speakers and returns the Speaker object
def pick_device():
    devices = sc.all_speakers()
    for x in range(0, len(devices)):
        print("{}: {} ({})".format(x, devices[x].name, devices[x].id))
    inp = int(input("Enter the device number: "))
    if inp > 0 and inp < len(devices):
        return devices[inp]
    else:
        print("Invalid number ", inp)
        return pick_device()


# Loads a file. Returns a numpy multidimentional array and the samplerate
# The numpy array is frames x channels and will always return data for 2 channels
def load_file(audio):
    data, samplerate = sf.read(audio, always_2d=True)
    return data, samplerate


# Plays an audio file split between the two devices. Flips if `flipped` gets set during playtime
# returns list of devices which may change due to flip
def play_file(audio_file, devices):
    print("Loading file", audio_file)
    data, sr = load_file(audio_file)
    col, row = data.shape
    print("Loaded")
    l = 0
    r = 1
    b_size = 128
    for x in range(0, int(row/b_size)):
        start = x * b_size
        end = (x+1) * b_size
        devices[r].play(data[start:end, 1], blocksize=b_size)
        devices[l].play(data[start:end, 0][start:end], blocksize=b_size)
        if flipped:
            t = l
            l = r
            r = t
            flipped = False
    if l != 1:
        print("Preserving flipped state")
        return [devices[l], devices[r]]
    else:
        return devices


# Sets two audio devices to be left and right speaker. Sets volume. 
# Returns a list of the two devices = [left_device, right_devices]
def configure():
    print("Pick the speaker to be the left speaker")
    left = pick_device()
    print("Pick the speaker to be the right speaker")
    right = pick_device()
    print("Position the speakers next to the device for calibration.")
    print("Press enter when ready")
    input()
    devices = normalize_loudness(left, right)
    return devices
    

def main():
    accel_thread = threading.Thread(target=read_accel_data())
    accel_thread.start()
    devices = configure()
    while True:
        f = input("Enter a filename to play:")
        devices = play_file(f, devices)


if __name__ == "__main__":
    main()

