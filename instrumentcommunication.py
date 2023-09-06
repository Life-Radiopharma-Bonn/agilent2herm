import socket
import time

HOST = "10.1.10.101"
PORT = 9100 # this needs to be 23 since agilent expects tehre to be a client

COUNTER=0
READCOUNTER=0

def readMsg(conn):
    buf = ""
    while '\n' not in buf:
        tmp = conn.recv(1)
        if tmp == b'\x0a':
            break
        #print(f"{tmp}" + " " + str(tmp))
        buf = buf + tmp.decode("ascii")
        #print(f"buffer: {buf}")
        #print(f"buffer: {buf}")
    print(f"buffer: {buf}")
    return buf.strip() #nur trimmed strings zurückgeben

def SYID(conn):
    #           SYID HP35900E, Rev E.02.04.32
    HEADER = """SYID HP35900E, Rev E.02.04.32""".encode("ascii")+b'\x0a'
    print(f"Sending SYID {HEADER}",flush=True)
    conn.sendall(HEADER)

def SYSN(conn):
    HEADER = """SYSN LIFERADIO1\n""".encode("ascii")
    print(f"Sending SYSN {HEADER}",flush=True)
    conn.sendall(HEADER)

def SYBP(conn):
    HEADER = """ARSP\nARRS\nARTM OFF\nAVRS\nAVSP\nARBM ?\n""".encode("ascii")
    print(f"Sending SYBP {HEADER}",flush=True)
    conn.sendall(HEADER)

def ARBM(conn,data):
    HEADER = """ARSP\nARRS\nARTM OFF\nAVRS\nAVSP\nARBM ?\n""".encode("ascii")
    print(f"Sending ARBM {HEADER}",flush=True)
    conn.sendall((data+"\n").encode("ascii"))

def AVTS(conn,data):
    HEADER = """ARLM SYSTEM\nARGR\nTTDL AXPRE\nTTDL AXINTO\nTTDL AXPOST\nTTCR AXPRE, HOST_CMD\nTTCR AXINTO, AR_START\nTTCR AXPOST, AR_STOP\nTTOP AXPRE, 0; SYNO\nTTOP AXINTO, 0; TTSP AXPRE\nTTOP AXINTO, 0; TTDS AXPRE\nTTOP AXPOST, 0; TTSP AXINTO\nTTOP AXPOST, 0; TTDS AXINTO\nTTEN AXPRE\nTTEN AXINTO\nTTEN AXPOST\n"""
    print(f"Sending AVTS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def ARSS(conn,data):
    HEADER = """ARSS READY, 0\n"""
    print(f"Sending ARSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def AVSS(conn,data):
    global COUNTER
    COUNTER = COUNTER + 1
    HEADER = """AVSS ON, 0, 5, 0, """ + str(int(COUNTER)) + """\n"""
    print(f"Sending AVSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def TTSS(conn,data):
    HEADER = """TTSS """+data.split(" ")[1]+""", ENABLED, -1, 0\n""".encode("ascii")
    print(f"Sending TTSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def AVRD(conn,data):
    global READCOUNTER
    READCOUNTER = READCOUNTER+1
    HEADER = """AVRD HEX, 001;0023 """+upper(hex(READCOUNTER))+"""\n""".encode("ascii")
    print(f"Sending AVRD {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def AVSL(conn,data):
    print(f"Received AVSL (sleep?) {data}",flush=True)

with socket.socket() as serversock:
    serversock.bind((HOST,PORT))
    serversock.listen()
    while True:
        conn, addr = serversock.accept() #this is blocking
#        conn.setsockopt(socket.IPPROTO_IPV4, socket.IPV4_DONTFRAG,1)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,4096*2)
#        conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,4096*2)

        with conn:
            print(f"New Connection from client {addr}")
            
            COUNTER=0
            READCOUNTER=0
    
            while True and not conn._closed and not conn.fileno()==-1:
                data = readMsg(conn)
                match data.split(" ")[0]:
                    case "SYID":
                        SYID(conn)
                    case "SYSN":
                        SYSN(conn)
                    case "SYBP":
                        SYBP(conn)

                    case "ARBM":
                        ARBM(conn, data)
                    case "ARSS":
                        ARSS(conn, data)
                    case "AVTS":
                        AVTS(conn, data)
                    case "AVSS":
                        AVSS(conn, data)
                    case "AVDF":
                        AVSS(conn, data)
                    case "AVRD":
                        AVRD(conn, data)
                    case "AVSL":
                        AVSL(conn, data)

                    case "TTSS":
                        TTSS(conn, data)
