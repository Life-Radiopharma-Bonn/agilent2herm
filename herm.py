import serial
import time
import os
import datetime

def readUntil(ser,stop):
    buf = ""
    while stop not in buf:
        buf = buf + ser.read(1).decode("ascii")
    return buf.strip()

def parseLine(line):
    return list(filter(None,line.split(" ")))

def persistValue(val):
    with open("/mnt/berthold/tmp","w") as f:
        f.write(str(int(val)))
    os.rename("/mnt/berthold/tmp","/mnt/berthold/latest")
    with open("/mnt/berthold/tmp_timestamp","w") as f:
        f.write(str(datetime.datetime.now().timestamp()))
    os.rename("/mnt/berthold/tmp_timestamp","/mnt/berthold/timestamp")


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
    ser.write(b'OUTPUTMODE 2\r\n')#2=1hz,1=10hz
    ser.flush()
    time.sleep(0.5)
    print(readUntil(ser,"\r\n"),flush=True)
    time.sleep(0.5)
    ser.write(b'SETCHANNEL 1\r\n')
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
        if 'signal' in line or 'Status' in line:
            continue
        #print(line)
        print(line,flush=True)
        cts = parseLine(line)[2]
        persistValue(cts)
