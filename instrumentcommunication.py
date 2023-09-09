import socket
import time
import random
import datetime

from multiprocessing import Process, Queue

HOST = "0.0.0.0"
PORT = 9100 # this needs to be 23 since agilent expects tehre to be a client
FAKTOR = 1000000.0

START = datetime.datetime.now()
DEBUG=True


INSTRUMENT_STATUS = "READY, 0"
RUNNING = False

METHODENLAUFZEIT = -1
RUN_STARTTIME=datetime.datetime.now()
RUN_STOPTIME=-1

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

COUNTER = 1
STATUS = 0
def ARSS(conn,data):
    global RUNNING
    global COUNTER
    global STATUS
    global RUN_STARTTIME
    if RUNNING:
        delta = int((datetime.datetime.now()-RUN_STARTTIME).total_seconds())
        HEADER = """ARSS RUN, """+str(delta)+"""\n"""
    else:
        HEADER = """ARSS READY, 0\n"""
        print(HEADER,flush=True)

    myprint(f"Sending ARSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

AVSSc=0
def AVSS(conn,data,q):
    global AVSSc
    global START
    global RUNNING
    delta = str(int((datetime.datetime.now()-START).total_seconds()*1000))
    state = "0"
    if RUNNING:
        state="5"
    HEADER = """AVSS ON, """+state+""", 5, """+str(min(q.qsize(),9))+""", """ + delta + """\n"""
    #HEADER = """AVSS ON, 0, 5, 2, """ + delta + """\n"""
    myprint(f"Sending AVSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def TTSS(conn,data):
    global RUNNING
    global RUN_STARTTIME
    global RUN_STOPTIME
    global METHODENLAUFZEIT
    HEADER=""
    myprint("TTSS"+data+"\tRUNNING:"+str(RUNNING)+"\tRUN_STARTTIME:"+str(RUN_STARTTIME)+"\tMETHODENLAUFZEIT:"+str(METHODENLAUFZEIT))
    if data.split(" ")[1]=="AXINTO":
        if not RUNNING:
            HEADER = """TTSS """+data.split(" ")[1]+""", ENABLED, -1, 0\n"""
        else:
            #delta = int((datetime.datetime.now()-RUN_STARTTIME).total_seconds()*1000)
            if int((datetime.datetime.now()-RUN_STARTTIME).total_seconds()*1000) < METHODENLAUFZEIT:
                delta = int((datetime.datetime.now()-RUN_STARTTIME).total_seconds()*1000)
                HEADER = """TTSS """+data.split(" ")[1]+""", RUNNING, """+str(delta)+""", """+str(METHODENLAUFZEIT)+"""\n"""
            else:
                RUN_STOPTIME=datetime.datetime.now()
                delta = int((RUN_STOPTIME-RUN_STARTTIME).total_seconds()*1000)
                HEADER = """TTSS """+data.split(" ")[1]+""", DISABLED, """+str(delta)+""", """+str(METHODENLAUFZEIT)+"""\n"""
    else:
        if not RUNNING:
            HEADER = """TTSS """+data.split(" ")[1]+""", ENABLED, -1, 0\n"""
        else:
            if data.split(" ")[1]=="AXPRE":
                HEADER = """TTSS """+data.split(" ")[1]+""", DISABLED, -1, 0\n"""
            else:
                HEADER = """TTSS """+data.split(" ")[1]+""", ENABLED, -1, 0\n"""
            
            if data.split(" ")[1]=="AXPOST":
                HEADER = """TTSS """+data.split(" ")[1]+""", ENABLED, -1, 0\n"""
                if RUN_STOPTIME != -1:
                    HEADER = """TTSS """+data.split(" ")[1]+""", DISABLED, 15, 0\n"""

    myprint(f"Sending TTSS {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def ARXR(conn,data):
    ARSP(conn,data)
    myprint(f"Received ARXR",flush=True)

def AVRD(conn,data,q):
    global AVSSc
    qsize = AVSSc

    HEADER = """AVRD HEX, 00"""+str(qsize)+""";"""
    for i in range(0,qsize):
        val_str = str(hex(encodeWert(q.get()))[2:]).upper().zfill(8)
        HEADER = HEADER + val_str
    HEADER = HEADER + "\n"
    myprint(f"Sending AVRD {HEADER}",flush=True)
    myprint(str(HEADER.encode("ascii")) + "\t" + str(len(str(HEADER.encode("ascii")))))
    conn.sendall(HEADER.encode("ascii"))

def AREV(conn,data,q):
    global RUNNING
    global RUN_STARTTIME
    global RUN_STOPTIME
    global START
    HEADER = ""
    if RUNNING:
        if (datetime.datetime.now()-RUN_STARTTIME).total_seconds()*1000 >= METHODENLAUFZEIT:
            RUN_STOPTIME = datetime.datetime.now()
            #RUNNING=False
        delta = str(int((RUN_STARTTIME-START).total_seconds()*1000))
        if RUN_STOPTIME == -1:
            HEADER = "AREV HOST, "+str(delta)+", 223; NONE\n"
        else:
            HEADER = "AREV HOST, "+str(delta)+", 223; HOST, "+str(int((RUN_STOPTIME-RUN_STARTTIME).total_seconds()*1000))+", 255\n"
    else:
        HEADER = "AREV NONE; NONE\n"

    myprint(f"Sending AREV {HEADER}",flush=True)
    conn.sendall(HEADER.encode("ascii"))

def AVDF(conn,data):
    global AVSSc
    AVSSc = int(data.split(" ")[2])
    #KEINE ANTWORT

def ARSP(conn,data):
    #STOP command
    global RUNNING
    global RUN_STARTTIME
    global RUN_STOPTIME
    global METHODENLAUFZEIT

    if RUNNING==True:
        myprint("_______________",flush=True)
        myprint("!RUNNING=FALSE!",flush=True)
        myprint("_______________",flush=True)
        RUNNING=False
        RUN_STARTTIME=-1
        RUN_STOPTIME=-1
        METHODENLAUFZEIT=-1
    #KEINE ANTWORT

    #KEINE ANTWORT

def ARGR(conn,data):
    #KEINE ANTWORT
#    global RUNNING
#    if RUNNING==False:
#        RUNNING = True
#        RUN_STARTTIME=datetime.datetime.now()
    #else:
    #    RUNNING=False
    pass

def ARCL(conn,data):
    #KEINE ANTWORT
    global RUNNING
    myprint("Received ARCL")
    #RUNNING = True
    #RUN_STARTTIME=datetime.datetime.now()
    ARSP(conn,data)
    pass

def TTOP(conn,data):
    global METHODENLAUFZEIT
    inp = data.split(" ")
    if inp[1]=="AXINTO,":
        METHODENLAUFZEIT = int(inp[2].split(";")[0])
        myprint("Received AXINTO - planned runtime:"+str(METHODENLAUFZEIT),flush=True)
    #KEINE ANTWORT
    pass

def TTEN(conn,data):
    global RUNNING
    myprint("Received TTEN"+data,flush=True)
    #KEINE ANTWORT
    pass

def ARST(conn,data):
    global RUNNING
    global RUN_STARTTIME
    myprint("Received ARST COMMAND "+data,flush=True)
    if RUNNING==False:
        RUNNING = True
        RUN_STARTTIME=datetime.datetime.now()
        myprint("_______________",flush=True)
        myprint("!RUNNING=TRUE!!",flush=True)
        myprint("_______________",flush=True)
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
        return 0
    #minimalen wert auf 0 setzen
    #damit erzeugen wir einen negativen wert am unteren ende. 
    #hoffentlich können wir damit fehler schneller erkennen, da wir keinen echten Status setzen können.

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
    def readTimestampDeltaFromFile():
        global INSTRUMENT_STATUS
        try:
            line = ""
            with open("/mnt/berthold/timestamp","r") as f:
                line = f.read()
            return (datetime.datetime.now()-datetime.datetime.fromtimestamp(int(line))).total_seconds()<2
        except Exception as e:
            print(e)
            return False 

    while True:
        myprint("herm side qsize: " +str(q.qsize()))
        if readTimestampDeltaFromFile():
            myprint("Valid value from herm received in the past 2s",flush=True)
            q.put(int(readFromFile()))
        else:
            myprint("!NO VALID VALUE FROM HERM - SENDING DUMMY NEGATIVE VALUE",flush=True)
            q.put(-1)
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
                elif data.split(" ")[0]=="ARSP":
                        ARSP(conn, data)
                elif data.split(" ")[0]=="ARST":
                        ARST(conn, data)
                else:
                    myprint("UNKNOWN PACKAGE:",flush=True)
                    myprint(data,flush=True)
                    pass
