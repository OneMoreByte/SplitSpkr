#/usr/bin/env python3

import soundcard as sc
import soundfile as sf
import numpy as np
import serial
import threading
import glob
import pulsectl

# Globals for thread data sharing
flipped = False
mic_data = []


# Runs as it's own thread. Reads the data from the accelerometer
def read_accel_data():
    global flipped
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
    global mic_data
    data = device.record(length, sr)
    mx = 0.0 
    for x in data[..., 0]:
        if x > mx:
            mx = x
    mic_data.append(mx)


def play_data(device, data, sr):
    with device.player(samplerate=sr) as sp:
        sp.play(data)


def get_pulse_speakers(pulse, devices):
    pulse_devices = [None, None]
    for dev in pulse.sink_list():
        if dev.description == devices[0].name:
            pulse_devices[0] = dev
            pulse.volume_set_all_chans(dev, 1.0)
        elif dev.description == devices[1].name:
            pulse_devices[1] = dev
            pulse.volume_set_all_chans(dev, 1.0)
    print(pulse_devices)
    return pulse_devices


def sample_volume(devices, mic): 
    global mic_data
    mic_data = []
    data, sr = load_file("./speaker-test.wav")
    row, col = data.shape 
    for x in range(2):
        t_mic = threading.Thread(target=record_playback, args=(mic, row, sr))
        t_spk = threading.Thread(target=play_data, args=(devices[x], data, sr))
        t_mic.start()
        t_spk.start()
        t_mic.join()
    for x in range(2):
        mic_data[x] = round(mic_data[x], 3)


# Compares the loudness of two devices and allows user to set volume
def normalize_loudness(dev_l, dev_r):
    global mic_data
    pulse = pulsectl.Pulse('SplitSpkr')
    devices = [dev_l, dev_r]
    pulse_devices = get_pulse_speakers(pulse, devices)
    mic = sc.default_microphone()
    for m in sc.all_microphones():
        if m.name == "USB PnP Audio Device Analog Mono":
            mic = m
    sample_volume(devices, mic)
    sample_volume(devices, mic)
    l_vol = mic_data[0]
    r_vol = mic_data[1]
    print(mic_data)
    if l_vol > r_vol:
        pulse.volume_set_all_chans(pulse_devices[0], \
                (r_vol/l_vol))
    else:
        pulse.volume_set_all_chans(pulse_devices[1], \
                (l_vol/r_vol))
    sample_volume(devices, mic)
    print(mic_data)
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
    global flipped
    print("Loading file", audio_file)
    data, sr = load_file(audio_file)
    row, col = data.shape
    #left_data, right_data = split_data(data)
    print("Loaded")
    l = 0
    r = 1
    b_size = 128

    with devices[l].player(sr, blocksize=b_size) as left, \
            devices[r].player(sr, blocksize=b_size) as right:
        for x in range(0, int(row/b_size)):
            start = x * b_size
            end = (x+1) * b_size
            left.play(data[start:end, 0])
            right.play(data[start:end, 1])
            if flipped:
                print("Output is flipped for next song")
                t = l
                l = r
                r = t
                flipped = False
    if l == 1:
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
    accel_thread = threading.Thread(target=read_accel_data, daemon=True)
    accel_thread.start()
    devices = configure()
    while True:
        f = input("Enter a filename to play:")
        devices = play_file(f, devices)
    

if __name__ == "__main__":
    main()

