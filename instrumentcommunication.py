import socket
import time
import random
import datetime

from multiprocessing import Process, Queue

HOST = "10.1.10.101"
PORT = 9100 # this needs to be 23 since agilent expects tehre to be a client
FAKTOR = 100000.0

START = datetime.datetime.now()

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
    print(f"Sending ARBM {data}",flush=True)
    conn.sendall((data+"\n").encode("ascii"))

def AVTS(conn,data):
    HEADER = """ARLM SYSTEM\nARGR\nTTDL AXPRE\nTTDL AXINTO\nTTDL AXPOST\nTTCR AXPRE, HOST_CMD\nTTCR AXINTO, AR_START\nTTCR AXPOST, AR_STOP\nTTOP AXPRE, 0; SYNO\nTTOP AXINTO, 0; TTSP AXPRE\nTTOP AXINTO, 0; TTDS AXPRE\nTTOP AXPOST, 0; TTSP AXINTO\nTTOP AXPOST, 0; TTDS AXINTO\nTTEN AXPRE\nTTEN AXINTO\nTTEN AXPOST\n"""
    print(f"Sending AVTS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def ARSS(conn,data):
    HEADER = """ARSS READY, 0\n"""
    print(f"Sending ARSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

AVSSc=1
def AVSS(conn,data,q):
    global AVSSc
    global START
    delta = str(int((datetime.datetime.now()-START).total_seconds()*1000))
    HEADER = """AVSS ON, 0, 5, """+str(q.qsize())+""", """ + delta + """\n"""
    #HEADER = """AVSS ON, 0, 5, 2, """ + delta + """\n"""
    print(f"Sending AVSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def TTSS(conn,data):
    HEADER = """TTSS """+data.split(" ")[1]+""", ENABLED, -1, 0\n"""
    print(f"Sending TTSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def AVRD(conn,data,q):
    qsize = q.qsize()

    DELIMITER="0023"
    HEADER = """AVRD HEX, 00"""+str(qsize)+""";"""
    for i in range(0,qsize):
        val_str = str(hex(encodeWert(q.get()))[2:]).upper().zfill(8)
        HEADER = HEADER + val_str
    HEADER = HEADER + "\n"
    print(f"Sending AVRD {HEADER}",flush=True)
    print(str(HEADER.encode("ascii")) + "\t" + str(len(str(HEADER.encode("ascii")))))
    conn.sendall(HEADER.encode("ascii"))

def AVDF(conn,data):
    global AVSSc
    AVSSc = int(data.split(" ")[2])
    #KEINE ANTWORT

def ATRD(conn,data):
    HEADER = """ATRD 255\n"""
    print(f"Sending ATRD(1) {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))
    
def AVSL(conn,data,q):
    i = data.split(" ")[1]
    if i == "?":
        HEADER = """AVSL 1000\n"""
        print(f"Sending AVSL {HEADER}",flush=True)
        conn.sendall(HEADER.encode("ascii"))
    else:
        print(f"Received AVSL (sleep?) {data}",flush=True)
        #time.sleep(1)
    #AVRD(conn,data,q)


def encodeWert(inp):
    ###nimmt einen wert (inp) entgegen und encoded ihn so, dass auf agilent-seite der wert so ankommt.
    #return int(((((inp+4)/FAKTOR) + 0.02281)/1e-8))

    #clippen am unteren ende
    mod_inp = inp
    if inp < 0:
        mod_inp=0
    #minimalen wert auf 0 setzen

    return min(int(((((mod_inp)/FAKTOR) + 0.02285)/1e-8)),4294967295) #0xffffffff ist maximum, diesen wert dürfen wir nicht überschreiten sonst gehts kaputt, lieber clippen wir hier

def herm_dummy_value_gen(q):
    print("starting herm dummy value gen")

    def readFromFile():
        try:
            line = ""
            with open("/mnt/berthold/latest","r") as f:
                line = f.read()
            return line
        except:
            return -1

    while True:
        print("herm side qsize: " +str(q.qsize()))
        q.put(int(readFromFile()))
        time.sleep(1)

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
            
            print("Starting 'measurement' thread for this client to enqueue values")
            q = Queue()
            p = Process(target=herm_dummy_value_gen, args=(q,))
            p.start()

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
                        AVSS(conn, data, q)
                    case "AVDF":
                        AVDF(conn, data)
                    case "AVRD":
                        AVRD(conn, data, q)
                    case "AVSL":
                        AVSL(conn, data, q)
                    case "ATRD":
                        ATRD(conn, data)

                    case "TTSS":
                        TTSS(conn, data)
