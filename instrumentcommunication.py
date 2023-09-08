import socket
import time
import random
import datetime

from multiprocessing import Process, Queue

HOST = "0.0.0.0"
PORT = 9100 # this needs to be 23 since agilent expects tehre to be a client
FAKTOR = 100000.0

START = datetime.datetime.now()
DEBUG=True


INSTRUMENT_STATUS = "READY, 0"
RUNNING = False

METHODENLAUFZEIT = -1
RUN_STARTTIME=datetime.datetime.now()

def myprint(msg,flush=True):
    global DEBUG
    if DEBUG:
        print(msg,flush=flush)

def readMsg(conn):
    buf = ""
    while '\n' not in buf:
        tmp = conn.recv(1)
        if tmp == b'\x0a':
            break
        #myprint(f"{tmp}" + " " + str(tmp))
        buf = buf + tmp.decode("ascii")
        #myprint(f"buffer: {buf}")
        #myprint(f"buffer: {buf}")
    myprint(f"buffer: {buf}")
    return buf.strip() #nur trimmed strings zurückgeben

def SYID(conn):
    #           SYID HP35900E, Rev E.02.04.32
    HEADER = """SYID HP35900E, Rev E.02.04.32""".encode("ascii")+b'\x0a'
    myprint(f"Sending SYID {HEADER}",flush=True)
    conn.sendall(HEADER)

def SYSN(conn):
    HEADER = """SYSN LIFERADIO1\n""".encode("ascii")
    myprint(f"Sending SYSN {HEADER}",flush=True)
    conn.sendall(HEADER)

def SYBP(conn):
    HEADER = """ARSP\nARRS\nARTM OFF\nAVRS\nAVSP\nARBM ?\n""".encode("ascii")
    myprint(f"Sending SYBP {HEADER}",flush=True)
    conn.sendall(HEADER)

def ARBM(conn,data):
    myprint(f"Sending ARBM {data}",flush=True)
    conn.sendall((data+"\n").encode("ascii"))

def AVTS(conn,data):
    HEADER = """ARLM SYSTEM\nARGR\nTTDL AXPRE\nTTDL AXINTO\nTTDL AXPOST\nTTCR AXPRE, HOST_CMD\nTTCR AXINTO, AR_START\nTTCR AXPOST, AR_STOP\nTTOP AXPRE, 0; SYNO\nTTOP AXINTO, 0; TTSP AXPRE\nTTOP AXINTO, 0; TTDS AXPRE\nTTOP AXPOST, 0; TTSP AXINTO\nTTOP AXPOST, 0; TTDS AXINTO\nTTEN AXPRE\nTTEN AXINTO\nTTEN AXPOST\n"""
    myprint(f"Sending AVTS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def ARSS(conn,data):
    global RUNNING
    if RUNNING:
        HEADER = """ARSS RUN, 5\n"""
    else:
        HEADER = """ARSS READY, 0\n"""

    myprint(f"Sending ARSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def AVSS(conn,data,q):
    global AVSSc
    global START
    delta = str(int((datetime.datetime.now()-START).total_seconds()*1000))
    HEADER = """AVSS ON, 0, 5, """+str(q.qsize())+""", """ + delta + """\n"""
    #HEADER = """AVSS ON, 0, 5, 2, """ + delta + """\n"""
    myprint(f"Sending AVSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def TTSS(conn,data):
    global RUNNING
    global RUN_STARTTIME
    global METHODENLAUFZEIT
    HEADER=""
    if data.split(" ")[1]=="AXINTO,":
        if not RUNNING:
            HEADER = """TTSS """+data.split(" ")[1]+""", ENABLED, -1, 0\n"""
        else:
            delta = str(int((datetime.datetime.now()-RUN_STARTTIME).total_seconds()*1000))
            HEADER = """TTSS """+data.split(" ")[1]+""", RUNNING, """+delta+""", """+str(METHODENLAUFZEIT)+"""\n"""
    else:
        HEADER = """TTSS """+data.split(" ")[1]+""", DISABLED, -1, 0\n"""

    myprint(f"Sending TTSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def AVRD(conn,data,q):
    qsize = q.qsize()

    HEADER = """AVRD HEX, 00"""+str(qsize)+""";"""
    for i in range(0,qsize):
        val_str = str(hex(encodeWert(q.get()))[2:]).upper().zfill(8)
        HEADER = HEADER + val_str
    HEADER = HEADER + "\n"
    myprint(f"Sending AVRD {HEADER}",flush=True)
    myprint(str(HEADER.encode("ascii")) + "\t" + str(len(str(HEADER.encode("ascii")))))
    conn.sendall(HEADER.encode("ascii"))

def AREV(conn,data,q):
    HEADER = "AREV NONE; NONE\n"
    myprint(f"Sending AREV {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def AVDF(conn,data):
    global AVSSc
    AVSSc = int(data.split(" ")[2])
    #KEINE ANTWORT

def ARGR(conn,data):
    #KEINE ANTWORT
    pass

def ARCL(conn,data):
    #KEINE ANTWORT
    global RUNNING
    RUNNING = True
    RUN_STARTTIME=datetime.datetime.now()

def TTOP(conn,data):
    global METHODENLAUFZEIT
    inp = data.split(" "))
    if inp[1].=="AXINTO,":
        METHODENLAUFZEIT = int(inp[2])
        myprint("Received AXINTO - planned runtime:"+str(planned_runtime),flush=True)
    #KEINE ANTWORT
    pass

def TTEN(conn,data):
    myprint("Received TTEN"+data,flush=True)
    #KEINE ANTWORT
    pass

def ATRD(conn,data):
    HEADER = """ATRD 255\n"""
    myprint(f"Sending ATRD(1) {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))
    
def AVSL(conn,data,q):
    i = data.split(" ")[1]
    if i == "?":
        HEADER = """AVSL 1000\n"""
        myprint(f"Sending AVSL {HEADER}",flush=True)
        conn.sendall(HEADER.encode("ascii"))
    else:
        myprint(f"Received AVSL (sleep?) {data}",flush=True)
        #time.sleep(1)
    #AVRD(conn,data,q)

def ARSM(conn,data,q):
    myprint(f"Received "+data,flush=True)
def BRSM(conn,data,q):
    myprint(f"Received "+data,flush=True)
def AVSP(conn,data,q):
    myprint(f"Received "+data,flush=True)


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
    myprint("starting herm dummy value gen")

    def readFromFile():
        global INSTRUMENT_STATUS
        try:
            line = ""
            with open("/mnt/berthold/latest","r") as f:
                line = f.read()
            return line
        except:
            INSTRUMENT_STATUS="NOT_READY, 130"
            return -1

    while True:
        myprint("herm side qsize: " +str(q.qsize()))
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
            myprint(f"New Connection from client {addr}")
            
            myprint("Starting 'measurement' thread for this client to enqueue values")
            q = Queue()
            p = Process(target=herm_dummy_value_gen, args=(q,))
            p.start()

            while True and not conn._closed and not conn.fileno()==-1:
                data = readMsg(conn)
                if data.split(" ")[0]=="SYID":
                        SYID(conn)
                elif data.split(" ")[0]=="SYSN":
                        SYSN(conn)
                elif data.split(" ")[0]=="SYBP":
                        SYBP(conn)
                elif data.split(" ")[0]=="ARBM":
                        ARBM(conn, data)
                elif data.split(" ")[0]=="ARGR":
                        ARGR(conn, data)
                elif data.split(" ")[0]=="ARCL":
                        ARCL(conn, data)
                elif data.split(" ")[0]=="ARXR":
                        ARXR(conn, data)
                elif data.split(" ")[0]=="ARSS":
                        ARSS(conn, data)
                elif data.split(" ")[0]=="AVTS":
                        AVTS(conn, data)
                elif data.split(" ")[0]=="AVSS":
                        AVSS(conn, data, q)
                elif data.split(" ")[0]=="AVDF":
                        AVDF(conn, data)
                elif data.split(" ")[0]=="AVRD":
                        AVRD(conn, data, q)
                elif data.split(" ")[0]=="AVSL":
                        AVSL(conn, data, q)
                elif data.split(" ")[0]=="ARSM":
                        ARSM(conn, data, q)
                elif data.split(" ")[0]=="BRSM":
                        BRSM(conn, data, q)
                elif data.split(" ")[0]=="AVSP":
                        AVSP(conn, data, q)
                elif data.split(" ")[0]=="AREV":
                        AREV(conn, data, q)
                elif data.split(" ")[0]=="ATRD":
                        ATRD(conn, data)
                elif data.split(" ")[0]=="TTSS":
                        TTSS(conn, data)
                elif data.split(" ")[0]=="TTOP":
                        TTOP(conn, data)
                else:
                    myprint("UNKNOWN PACKAGE:",flush=True)
                    myprint(data,flush=True)
                    pass
