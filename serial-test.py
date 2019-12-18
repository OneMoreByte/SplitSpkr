import serial

accel = serial.Serial('/dev/ttyACM0')
state = "n"
direction = "Forward"
while True:
    inp = accel.readline().decode("utf-8").strip().split()
    if inp and len(inp) == 3:
        x = int(inp[0])
        y = int(inp[1])
        z = int(inp[2])
        if x == 0 and y == 0 and state != "F" and state == "N":
            print("Flip")
            if direction == "Forward":
                direction = "Backward"
            else:
                direction = "Forward"
            print(direction)
            state = "F"
        elif x == 0 and y == 1 and state != "N":
            print("Neutral")
            state = "N"
        
    accel.reset_input_buffer()


