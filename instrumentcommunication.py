import socket
import time
import random
import datetime
import math

from multiprocessing import Process, Queue
from enum import Enum
import signal
from socket import socket


class ProcessKiller:
    SHOULD_END = False

    def exit_gracefully(self, *args):
        print("RECEIVED STOP SIGNAL - PREPARING TO END")
        self.SHOULD_END = True

    def __init__(self):
        print("Setting up process killer for sigint and sigterm", flush=True)
        signal.signal(signal.SIGINT, self.exit_gracefully)
        # signal.signal(signal.SIGTERM,self.exit_gracefully)


class InstrumentState(Enum):
    IDLE = 0
    PRERUN = 1
    RUN = 2
    POSTRUN = 3


HOST = "0.0.0.0"
PORT = 9100  # 9100 for the instrment communication, 23 for the telnet service
FAKTOR = 1000000.0

START = datetime.datetime.now()  # this is the start time of the instrument
DEBUG = True
killer = ProcessKiller()

READY_STATE = ""
RUNNING = False

METHODENLAUFZEIT = -1
RUN_STARTTIME = datetime.datetime.now()
RUN_STOPTIME = -1


def myprint(msg, flush=True):
    global DEBUG
    if DEBUG:
        print(msg, flush=flush)


def readMsg(conn):
    buf = ""
    while '\n' not in buf:
        tmp = conn.recv(1)
        if tmp == b'\x0a':
            break
        # myprint(f"{tmp}" + " " + str(tmp))
        buf = buf + tmp.decode("ascii")
        # myprint(f"buffer: {buf}")
        # myprint(f"buffer: {buf}")
    myprint(f"buffer: {buf}")
    return buf.strip()  # nur trimmed strings zurückgeben


def SYID(conn):
    """Returns the System ID
    Req: "SYID\\n"
    Resp: "SYID HP35900E, Rev E.02.04.32\\n"
    """
    HEADER = """SYID HP35900E, Rev E.02.04.32\n""".encode("ascii")
    myprint(f"Sending SYID {HEADER}", flush=True)
    conn.sendall(HEADER)


def SYSN(conn):
    """Returns the System Serial Number

    Req: "SYSN\\n"
    Resp: "SYSN XXXXXXXXXXX\\n"
    """
    HEADER = """SYSN LIFERADIO1\n""".encode("ascii")
    myprint(f"Sending SYSN {HEADER}", flush=True)
    conn.sendall(HEADER)


def ARBM(conn, data):
    """Channel A Request Button Mode

    Req: "ARBM ?\\n"
    Resp:"ARBM OFF, OFF\\n"
    """
    myprint(f"Sending ARBM {data}", flush=True)
    result = ""
    # if data.split(" ")[1] == "?":
    result = "ARBM OFF, OFF\n"
    conn.sendall(result.encode("ascii"))


def ARSS(conn, data):
    """Channel A RUN SYSTEM STATE
    Requests the current system state regarding a run.

    The typical Response is
    Resp: ARSS STATUS_TEXT, STATUS_CODE\\n

    In Online-Mode this usually looks like
    Req: "ARSS\\n"
    Resp:"ARSS READY, 0\\n"

    However during a measurement, the STATUS_TEXT changes to "RUN" with the STATUS_CODE becoming a seconds counter?

    Req: "ARSS\\n"
    Resp:"ARSS RUN, 5\\n"

    THIS SWITCH ONLY HAPPENS IF THIS INSTRUMENT IS RUNNING ALONE WITHOUT ANY OTHERS INTERACTING WITH IT.
    NOT GOING TO BE IMPLEMENTED AS THIS IS NOT A REQUIREMENT FOR US CURRENTLY
    
    Typically the Interval changes in Steps of 128, so once enough time has passed, (128s) this will become 5+128=133

    Req: "ARSS\\n"
    Resp:"ARSS RUN, 133\\n"

    etc.

    Also there is a Status NOT_READY, that is being used AFTER measurements, maybe to indicate a clean stop?
    For NOT_READY the Code is typically 130 or 142 in my tests. (+x*4 basically)

    """
    global RUNNING
    global RUN_STARTTIME
    global READY_STATE
    HEADER = ""
    if RUNNING:
        delta = int((datetime.datetime.now() - RUN_STARTTIME).total_seconds())
        if READY_STATE == "":
            HEADER = """ARSS RUN, 5\n"""
    else:
        HEADER = """ARSS READY, 0\n"""
        print(HEADER, flush=True)

    if READY_STATE != "":
        HEADER = READY_STATE

    myprint(f"Sending ARSS {HEADER}", flush=True)
    conn.sendall(HEADER.encode("ascii"))


number_of_items_request = 0


def AVSS(conn, data, q):
    """Returns the Channel A Value and System State
    
    Requests always look like
    AVSS\\n

    Responses are shaped like:
    AVSS [ON|OFF], X, 5, ITEMS_IN_QUEUE, MILLISECONDS_SINCE_INSTRUMENT_START\\n

    With X 
        Outside of Runs
            X=0 
        In Runs
            X=5
            After 124 seconds into the run
            X=133 and stays there.

    The Switch between ON and OFF only seems to be used after an acquisition.
    """
    global number_of_items_request
    global START
    global RUNNING
    global READY_STATE
    delta = str(int((datetime.datetime.now() - START).total_seconds() * 1000))
    state = "0"
    if RUNNING:
        state = "5"
    if not RUNNING and READY_STATE != "":
        state = "14"
    HEADER = """AVSS ON, """ + state + """, 5, """ + str(min(q.qsize(), 9)) + """, """ + delta + """\n"""
    # HEADER = """AVSS ON, 0, 5, 2, """ + delta + """\n"""
    myprint(f"Sending AVSS {HEADER}", flush=True)
    conn.sendall(HEADER.encode("ascii"))


def TTSS(conn, data):
    """Method to request current TimeTable (TT) System Status(SS)
    The possible States are
    AXPRE
    AXINTO
    AXPOST
    
    For Usage of channel A.
    For Channel B these might be
    BXPRE
    BXINTO
    BXPOST

    A typical request looks like
    Req: TTSS AXINTO\\n

    When not in an active acquisition, the response might look like
    Resp: TTSS AXINTO, ENABLED, -1, 0\\n
    The other States behave accordingly.

    During an active Measurement, the Result changes to

        "TTSS AXINTO, RUNNING, [TIME_SINCE_START_IN_MS], [TOTAL_PLANNED_TIME]\\n"
    If the AXINTO state is currently being executed.

    After being executed, the State changes to DISABLED

    like
        "TTSS AXINTO, DISABLED, 15001, 15000\\n"

    """
    global RUNNING
    global RUN_STARTTIME
    global RUN_STOPTIME
    global METHODENLAUFZEIT
    global READY_STATE
    HEADER = ""
    myprint("TTSS" + data + "\tRUNNING:" + str(RUNNING) + "\tRUN_STARTTIME:" + str(
        RUN_STARTTIME) + "\tMETHODENLAUFZEIT:" + str(METHODENLAUFZEIT))
    if data.split(" ")[1] == "AXINTO":
        if not RUNNING:
            HEADER = """TTSS """ + data.split(" ")[1] + """, ENABLED, -1, 0\n"""
        else:
            # delta = int((datetime.datetime.now()-RUN_STARTTIME).total_seconds()*1000)
            if int((datetime.datetime.now() - RUN_STARTTIME).total_seconds() * 1000) < METHODENLAUFZEIT:
                delta = int((datetime.datetime.now() - RUN_STARTTIME).total_seconds() * 1000)
                HEADER = """TTSS """ + data.split(" ")[1] + """, RUNNING, """ + str(delta) + """, """ + str(
                    METHODENLAUFZEIT) + """\n"""
            else:
                HEADER = """TTSS """ + data.split(" ")[1] + """, DISABLED, """ + str(
                    METHODENLAUFZEIT + 30) + """, """ + str(METHODENLAUFZEIT) + """\n"""
                if RUN_STOPTIME == -1:
                    RUN_STOPTIME = datetime.datetime.now()
                    READY_STATE = "ARSS NOT_READY, 14\n"


    else:
        if not RUNNING:
            HEADER = """TTSS """ + data.split(" ")[1] + """, ENABLED, -1, 0\n"""
        else:
            if data.split(" ")[1] == "AXPRE":
                HEADER = """TTSS """ + data.split(" ")[1] + """, DISABLED, -1, 0\n"""
            else:
                HEADER = """TTSS """ + data.split(" ")[1] + """, ENABLED, -1, 0\n"""

            if data.split(" ")[1] == "AXPOST":
                HEADER = """TTSS """ + data.split(" ")[1] + """, ENABLED, -1, 0\n"""
                if RUN_STOPTIME != -1:
                    HEADER = """TTSS """ + data.split(" ")[1] + """, DISABLED, 15, 0\n"""

    myprint(f"Sending TTSS {HEADER}", flush=True)
    conn.sendall(HEADER.encode("ascii"))


def ARXR(conn, data):
    # ARSP(conn,data)
    myprint(f"Received ARXR", flush=True)


def AVRD(conn, data, q):
    """Channel A Value Read - Returns X items from the Instrument Queue
    
    Example:
    Req: AVRD\\n
    Resp: AVRD HEX, 002;01234567ABCDEF12\\n
    Returns the 2 Values 01234567 and ABCDEF12 in order.
    These will simply be appended to the OpenLab Queue (left to right)

    Any number must be 8 bytes
    """
    global number_of_items_request
    qsize = number_of_items_request

    HEADER = """AVRD HEX, 00""" + str(qsize) + """;"""
    for i in range(0, qsize):
        val_str = str(hex(encode_value(q.get()))[2:]).upper().zfill(8)
        HEADER = HEADER + val_str
    HEADER = HEADER + "\n"
    myprint(f"Sending AVRD {HEADER}", flush=True)
    myprint(str(HEADER.encode("ascii")) + "\t" + str(len(str(HEADER.encode("ascii")))))
    conn.sendall(HEADER.encode("ascii"))


def AREV(conn, data, q):
    """Channel A REference Value
    
    Default:
        Req: "AREV\\n"
        Resp: "AREV NONE; NONE\\n"

    In Independent mode (lowest button in OpenLab)
    During a Run this denominates the injection time based on the instrument start time (ARSS)
    So after Injection this turns into
        Req: "AREV\\n"
        Resp:"AREV HOST, [MILLIS_SINCE_INSTRUMENT_START_UNTIL_INJECTION], 223; NONE\\n"

    When the Run finished (AXINTO went through and is disabled)
        Req: "AREV\\n"
        Resp:"AREV HOST, [MILLIS_SINCE_INSTRUMENT_START_UNTIL_INJECTION], 223; HOST, [MILLIS_SINCE_INSTRUMENT_START_UNTIL_RUNEND], 255\\n"

    """
    global RUNNING
    global RUN_STARTTIME
    global RUN_STOPTIME
    global START
    HEADER = ""
    if RUNNING:
        # if (datetime.datetime.now()-RUN_STARTTIME).total_seconds()*1000 >= METHODENLAUFZEIT and METHODENLAUFZEIT != -1:
        # if RUN_STOPTIME == -1:
        #        RUN_STOPTIME = datetime.datetime.now()
        # RUNNING=False
        delta = str(int((RUN_STARTTIME - START).total_seconds() * 1000))
        if RUN_STOPTIME == -1:
            HEADER = "AREV HOST, " + str(delta) + ", 223; NONE\n"
        else:
            HEADER = "AREV HOST, " + str(delta) + ", 223; HOST, " + str(
                int((RUN_STOPTIME - START).total_seconds() * 1000)) + ", 223\n"
    else:
        HEADER = "AREV NONE; NONE\n"

    myprint(f"Sending AREV {HEADER}", flush=True)
    conn.sendall(HEADER.encode("ascii"))


def AVDF(conn, data):
    """Prepares the Data to be transmitted in the next AVRD request.
    The Number of items will be parsed out of the AVSS Packet

    Req: AVDF\\n
    --NO RESPONSE--"""
    global number_of_items_request
    number_of_items_request = int(data.split(" ")[2])
    # KEINE ANTWORT


def ARSP(conn, data):
    """Channel A Run STOP

    Req: "ARSP\\n"
    NO RESPONSE
    """
    # STOP command
    global RUNNING
    global RUN_STARTTIME
    global RUN_STOPTIME
    global METHODENLAUFZEIT
    myprint(f"Received ARSP - {data}", flush=True)

    if RUNNING == True:
        myprint("_______________", flush=True)
        myprint("!RUNNING=FALSE!", flush=True)
        myprint("_______________", flush=True)
        RUNNING = False
        RUN_STARTTIME = -1
        RUN_STOPTIME = -1
        METHODENLAUFZEIT = -1
    # KEINE ANTWORT

    # KEINE ANTWORT


def ARGR(conn, data):
    """Channel A Get Ready"""
    global READY_STATE
    global METHODENLAUFZEIT
    global RUN_STARTTIME
    global RUN_STOPTIME
    global RUNNING
    if READY_STATE != "":
        myprint("Received ARGR - setting ready-state from " + READY_STATE + " to \"\"")
        READY_STATE = ""
        if RUNNING:
            myprint("STOPPING RUN!", flush=True)
            RUN_STARTTIME = -1
            RUN_STOPTIME = -1
            METHODENLAUFZEIT = -1
            RUNNING = False


def TTOP(conn, data):
    global METHODENLAUFZEIT
    inp = data.split(" ")
    if inp[1] == "AXINTO,":
        METHODENLAUFZEIT = int(inp[2].split(";")[0])
        myprint("Received AXINTO - planned runtime:" + str(METHODENLAUFZEIT), flush=True)
    # KEINE ANTWORT
    pass


def ARST(conn, data):
    """Channel A RUN START
    Req: "ARST\\n"
    NO RESPONSE
    """
    global RUNNING
    global RUN_STARTTIME
    myprint("Received ARST COMMAND " + data, flush=True)
    if RUNNING == False:
        RUNNING = True
        RUN_STARTTIME = datetime.datetime.now()
        myprint("_______________", flush=True)
        myprint("!RUNNING=TRUE!!", flush=True)
        myprint("_______________", flush=True)
    # KEINE ANTWORT
    pass


def ATRD(conn, data):
    """Seems to be Either
    - Basic PING/PONG functionality
    or
    - To Issue an AD-Conversion for data to be ready during the next request of it

    We will answer statically with 255 here, which seems to be an "alright on our end"
    """
    HEADER = """ATRD 255\n"""
    conn.sendall(HEADER.encode("ascii"))


def AVSL(conn, data, q):
    """Channel A Value SampLing (AVSL)
    This either requests or sets the current sampling rate"""
    i = data.split(" ")[1]

    # this is a request - lets answer with "AVSL 1000\n" (=1Hz)
    if i == "?":
        HEADER = """AVSL 1000\n"""
        conn.sendall(HEADER.encode("ascii"))


def encode_value(inp: int) -> int:
    ###nimmt einen wert (inp) entgegen und encoded ihn so, dass auf agilent-seite der wert so ankommt.
    # return int(((((inp+4)/FAKTOR) + 0.02281)/1e-8))

    # clippen am unteren ende
    mod_inp = inp
    if inp < 0:
        mod_inp = 0
        return 0
    # minimalen wert auf 0 setzen
    # damit erzeugen wir einen negativen wert am unteren ende.
    # hoffentlich können wir damit fehler schneller erkennen, da wir keinen echten Status setzen können.

    return min(int(((((mod_inp) / FAKTOR) + 0.02285) / 1e-8)),
               4294967295)  # 0xffffffff ist maximum, diesen wert dürfen wir nicht überschreiten sonst gehts kaputt, lieber clippen wir hier


def herm_dummy_value_gen(q, killer):
    myprint("starting herm dummy value gen")

    def readFromFile():
        global INSTRUMENT_STATUS
        try:
            line = ""
            with open("/mnt/berthold/latest", "r") as f:
                line = f.read()
            return line.strip()
        except:
            INSTRUMENT_STATUS = "NOT_READY, 130"
            return -1

    # i = inotify.adapters.Inotify()
    # i.add_watch("/mnt/berthold/latest")

    # while True:
    #    events = i.event_gen(yield_nones=False, timeout_s=1)
    #    events = list(events)
    #    print(events)
    #    if len(events) > 0:
    #    #for i in events:
    #    #    (_, type_names, path, filename) = i
    #    #    if filename=="latest" and  'IN_MOVED_TO' in type_names:
    #        q.put(int(readFromFile()))
    #        myprint("Got data from HERM")
    #    else:
    #        myprint("No data from HERM")
    #        q.put(-100)

    time.sleep(
        3)  # ungefähr 6 sekunden dauert die inistialisierung des UIB2, daher bringen wir so die Signale übereinander

    start_time = datetime.datetime.now()
    iteration = 0

    while not killer.SHOULD_END:
        myprint("herm side qsize: " + str(q.qsize()))
        if q.qsize() > 100:
            print("client seems gone - dieing this thread")
            break
        # if readTimestampDeltaFromFile():
        #    myprint("Valid value from herm received in the past 2s",flush=True)
        buf = ""
        while buf == "":
            try:
                buf = readFromFile()
            except:
                pass
        q.put(int(buf))
        # else:
        #    myprint("!NO VALID VALUE FROM HERM - SENDING DUMMY NEGATIVE VALUE",flush=True)
        #    q.put(-1)

        tmp_time = datetime.datetime.now()
        delta = tmp_time - start_time
        to_sleep = delta.total_seconds()
        iteration = iteration + 1

        for i in range(0, int(to_sleep - iteration)):
            iteration = iteration + 1
            q.put(int(buf))
            print(f"discrepancy between {to_sleep} and {iteration} putting additional data:{i}")
            if iteration % 8505 == 0:
                print(f"discrepancy 8505 step second without increasing iterations counter")
                q.put(int(buf))

        # if iteration < 15:
        #    time.sleep(1.0)
        # else:
        #    #1.0022380
        #    avg_sleep = to_sleep/iteration - 1.0
        #    time.sleep(1.00-avg_sleep)
        #    print(f"{avg_sleep} avg-sleep")
        time.sleep(1.0)


class VirtualInstrument:
    """A simple class for emulating the communications protocol of an Agilent/HP 35900E Series II"""

    def __init__(self):
        self.state = InstrumentState.IDLE
        self.start_time = datetime.datetime.now()
        self.run_start_time = -1
        self.run_stop_time = -1
        self.method_runtime = -1

    def abort_run(self):
        self.method_runtime = -1
        self.run_stop_time = -1
        self.run_start_time = -1
        self.state = InstrumentState.IDLE

    def start_run(self):
        if self.state == InstrumentState.IDLE:
            self.state = InstrumentState.PRERUN
            return

        if self.state == InstrumentState.PRERUN:
            self.state = InstrumentState.RUN
            self.run_start_time = datetime.datetime.now()
            return

    def get_method_runtime_elapsed_ms(self):
        return int((datetime.datetime.now() - self.start_time).total_seconds() * 1000)

    def is_running(self):
        if self.get_method_runtime_elapsed_ms() < self.method_runtime:
            return True
        else:
            if self.run_stop_time == -1:
                self.run_stop_time = datetime.datetime.now()
            return False

    def set_method_runtime(self, runtime):
        self.method_runtime = runtime


def InstrumentClient(conn, q, killer, client_id):
    while not killer.SHOULD_END and not conn._closed and not conn.fileno() == -1:
        print(f"[{client_id}]KILLER:" + str(killer.SHOULD_END), flush=True)
        data = readMsg(conn)
        if data.split(" ")[0] == "SYID":
            SYID(conn)
        elif data.split(" ")[0] == "SYSN":
            SYSN(conn)
        elif data.split(" ")[0] == "ARBM":
            ARBM(conn, data)
        elif data.split(" ")[0] == "ARGR":
            ARGR(conn, data)
        elif data.split(" ")[0] == "ARXR":
            ARXR(conn, data)
        elif data.split(" ")[0] == "ARSS":
            ARSS(conn, data)
        elif data.split(" ")[0] == "AVSS":
            AVSS(conn, data, q)
        elif data.split(" ")[0] == "AVDF":
            AVDF(conn, data)
        elif data.split(" ")[0] == "AVRD":
            AVRD(conn, data, q)
        elif data.split(" ")[0] == "AVSL":
            AVSL(conn, data, q)
        elif data.split(" ")[0] == "AREV":
            AREV(conn, data, q)
        elif data.split(" ")[0] == "ATRD":
            ATRD(conn, data)
        elif data.split(" ")[0] == "TTSS":
            TTSS(conn, data)
        elif data.split(" ")[0] == "TTOP":
            TTOP(conn, data)
        elif data.split(" ")[0] == "ARSP":
            ARSP(conn, data)
        elif data.split(" ")[0] == "ARST":
            ARST(conn, data)
        else:
            myprint("UNKNOWN / UNUSED PACKET:", flush=True)
            myprint(data, flush=True)
    if not conn._closed:
        conn.close()


vi = VirtualInstrument()  # create this only once, this will be controlled by all the incoming commands
server_sock: socket
with socket.socket() as server_sock:
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen()
    client_id = 0
    while not killer.SHOULD_END:
        conn, addr = server_sock.accept()  # this is blocking
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096 * 2)
        client_id = client_id + 1

        with conn:
            myprint(f"New Connection from client {addr} - id {client_id}")

            myprint("Starting 'measurement' thread for this client to enqueue values")
            q = Queue()
            p = Process(target=herm_dummy_value_gen, args=(q, killer))
            p.start()

            p2 = Process(target=InstrumentClient, args=(conn, q, killer, client_id))
            p2.start()

    server_sock.shutdown(socket.SHUT_RDWR)
    server_sock.close()
    print("END!")
