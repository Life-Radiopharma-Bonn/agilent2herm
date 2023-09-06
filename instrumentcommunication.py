import socket
import time

HOST = "10.1.2.181"
PORT = 9100 # this needs to be 23 since agilent expects tehre to be a client


def readMsg(conn):
    buf = ""
    while '\n' not in buf:
        tmp = conn.recv(1)
        if tmp == b'\x0a':
            break
        try:
            print(f"{tmp}" + " " + str(tmp))
            buf = buf + tmp.decode("ascii")
            #print(f"buffer: {buf}")
        except:
            pass
        #print(f"buffer: {buf}")
    print(f"buffer: {buf}")
    return buf.strip() #nur trimmed strings zurückgeben

def SYID(conn):

    #           SYID HP35900E, Rev E.02.04.32
    HEADER = """SYID HP35900E, Rev E.02.04.32""".encode("ascii")+b'\x0a'
    print(f"Sending SYID {HEADER}",flush=True)
    conn.sendall(HEADER)

def SYSN(conn):
    HEADER = """SY SN LR12345678\n""".encode("ascii")
    print(f"Sending SYSN {HEADER}",flush=True)
    conn.sendall(HEADER)


with socket.socket() as serversock:
    serversock.bind((HOST,PORT))
    serversock.listen()
    while True:
        conn, addr = serversock.accept() #this is blocking
        with conn:
            print(f"New Connection from client {addr}")
            
            ###send header
            
            #tmp = readMsg(conn)
    
            while True:
                data = readMsg(conn)
                match data:
                    case "SYID":
                        SYID(conn)
                        break
                    case "SYSN":
                        SYSN(conn)
                    case "?":
                        questionmarkCommand(conn)
