import socket

HOST = "10.1.2.181"
PORT = 23 # this needs to be 23 since agilent expects tehre to be a client


def readMsg(conn):
    buf = ""
    while "\r" not in buf:
        tmp = conn.recv(1)
        try:
            #print("{tmp}" + " " + str(tmp))
            buf = buf + tmp.decode("ascii")
            #print(f"buffer: {buf}")
        except:
            pass
        #print(f"buffer: {buf}")
    print(f"buffer: {buf}")
    return buf.strip() #nur trimmed strings zurückgeben

def sendHeader(conn):
    HEADER = """\r\n===\r\n""".encode("ascii") + b'\xff\xfc\x01'+"""Agilent 35900 Series II\r\nPlease type "?" for HELP, or "/" for current settings\r\n""".encode("ascii")

    print("Sending Header {HEADER}",flush=True)
    conn.sendall(HEADER)

    conn.sendall(b'\x3e') #sends ">" to indicate a prompt

def quitCommand(conn):
    print("QuitCommand")
    exit()

def slashCommand(conn):
    print("SlashCommand")
    #print all info strings
    pass

def questionmarkCommand(conn):
    #send all help strings
    print("QuestionmarkCommand")
    pass


with socket.socket() as serversock:
    serversock.bind((HOST,PORT))
    serversock.listen()
    conn, addr = serversock.accept() #this is blocking
    with conn:
        print(f"New Connection from client {addr}")
        
        ###send header
        sendHeader(conn)
        
        #first message is nonsense, so take it and remove it
        readMsg(conn)

        while True:
            data = readMsg(conn)
            match data:
                case "quit":
                    quitCommand(conn)
                case "/":
                    slashCommand(conn)
                case "?":
                    questionmarkCommand(conn)
