import serial
import time
import os

def readUntil(ser,stop):
    buf = ""
    while stop not in buf:
        buf = buf + ser.read(1).decode("ascii")
    return buf.strip()

def parseLine(line):
    return list(filter(None,line.split(" ")))

def persistValue(val):
    with open("/mnt/berthold/tmp","w") as f:
        f.write(str(val))
    os.rename("/mnt/berthold/tmp","/mnt/berthold/latest")


with serial.Serial("/dev/ttyUSB0",19200,timeout=10) as ser:
    print("removing old data:"+ser.read(ser.in_waiting).decode("ascii"))
    ser.write(b'MEANVALUE 1\r\n')
    ser.flush()
    print(readUntil(ser,"\r\n"),flush=True)

    time.sleep(0.5)

    ser.write(b'HWZ 0\r\n')
    ser.flush()
    time.sleep(0.5)
    print(readUntil(ser,"\r\n"),flush=True)
    time.sleep(0.5)
    ser.write(b'OUTPUTMODE 2\r\n')
    ser.flush()
    time.sleep(0.5)
    print(readUntil(ser,"\r\n"),flush=True)
    time.sleep(0.5)
    ser.write(b'SETCHANNEL 2\r\n')
    ser.flush()
    time.sleep(0.5)
    print(readUntil(ser,"\r\n"),flush=True)
    time.sleep(0.5)
    ser.write(b'START 1\r\n')
    ser.flush()
    time.sleep(0.5)
    print(readUntil(ser,"\r\n"),flush=True)
    time.sleep(0.5)
    print(readUntil(ser,"\r\n"),flush=True)
    time.sleep(0.5)
    print(readUntil(ser,"\r\n"),flush=True)
    time.sleep(0.5)
    print(readUntil(ser,"\r\n"),flush=True)
    print(readUntil(ser,"\r\n"),flush=True)
    time.sleep(0.5)
    while True:
        line = readUntil(ser,"\r\n") #headerzeile ignorieren
        cts = parseLine(line)[2]
        persistValue(cts)
        print(".",end="",flush=True)
