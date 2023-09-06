import socket
import time

HOST = "10.1.2.181"
SUBNET_MASK="255.255.255.0"
GATEWAY="10.1.2.1"
PORT = 23 # this needs to be 23 since agilent expects tehre to be a client


def readMsg(conn):
    buf = ""
    while "\n" not in buf:
        tmp = conn.recv(1)
        if tmp == b'\xff':
            print("received b'\xff' - ignoring upcoming 2 bytes")
            # zwei weitere byte lesen und alle drei verwerfen
            conn.recv(2)
            continue
        try:
            print("{tmp}" + " " + str(tmp))
            buf = buf + tmp.decode("ascii")
            #print(f"buffer: {buf}")
        except:
            pass
        #print(f"buffer: {buf}")
    print(f"buffer: {buf}")
    return buf.strip() #nur trimmed strings zurückgeben

def sendHeader(conn):
    HEADER = """\r\n===""".encode("ascii") + b'\xff\xfc\x01'+"""Agilent 35900 Series II\r\nPlease type "?" for HELP, or "/" for current settings\r\n""".encode("ascii")

    print(f"Sending Header {HEADER}",flush=True)
    conn.sendall(HEADER)

    conn.sendall(b'\x3e') #sends ">" to indicate a prompt

def quitCommand(conn):
    print("QuitCommand")
    conn.close()

def slashCommand(conn):
    print("SlashCommand")
    RESPONSE = ""
    RESPONSE = RESPONSE + "   ===JetDirect Telnet Configuration===\n\r"
    RESPONSE = RESPONSE + "Firmware Rev.: E.02.04.32\r\n"
    RESPONSE = RESPONSE + "MAC Address: 00:aa:bb:cc:dd:ee\r\n"
    RESPONSE = RESPONSE + "Config By: USER SPECIFIED\r\n\r\n"
    RESPONSE = RESPONSE + "IP Address: "+HOST+"\r\n"
    RESPONSE = RESPONSE + "Subnet Mask: "+SUBNET_MASK+"\r\n"
    RESPONSE = RESPONSE + "Default Gateway: "+GATEWAY+"\r\n"
    RESPONSE = RESPONSE + "DHCP Config: Disabled\r\n"
    RESPONSE = RESPONSE + ">"
    conn.sendall(RESPONSE.encode("ascii"))
    print(f"Sending response {RESPONSE}")

    #print all info strings
    pass

def questionmarkCommand(conn):
    #send all help strings
    print("QuestionmarkCommand")
    pass


with socket.socket() as serversock:
    serversock.bind((HOST,PORT))
    serversock.listen()
    while True:
        conn, addr = serversock.accept() #this is blocking
        with conn:
            print(f"New Connection from client {addr}")
            
            ###send header
            sendHeader(conn)
            
            #tmp = readMsg(conn)
    
            while True:
                data = readMsg(conn)
                match data:
                    case "quit":
                        quitCommand(conn)
                        break
                    case "/":
                        slashCommand(conn)
                    case "?":
                        questionmarkCommand(conn)
