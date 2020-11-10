#!/usr/bin/env phython3

import sys
import socket
import selectors
import traceback
from datetime import datetime
import threading

import fixlibclient

sel = selectors.DefaultSelector()


def create_login_request(sender_comp_id, target_comp_id, send_seq_num):

    login_list = []

    login_list.append(("35", "A"))  # MsgType
    login_list.append(("34", send_seq_num))  # MsgSeqNum
    login_list.append(("49", sender_comp_id))  # SenderCompID
    login_list.append(("52", getSendingTime()))  # SendingTime
    # login_list.append(("52", "20201105-22:45:07.767"))  # SendingTime
    login_list.append(("56", target_comp_id))  # TargetCompID
    login_list.append(("98", "0"))  # EncryptMethod
    login_list.append(("108", "30"))  # HeartBeatInt
    login_list.append(("141", "N"))  # ResetSeqNumFlag


    login_request = b''
    for login_tag in login_list:
        login_request = login_request + bytes(login_tag[0] + "=" + login_tag[1], encoding="utf-8") + b'\x01'

    bodyLength = len(login_request)  # 9 - BodyLength

    login_request = bytes("8=FIX.4.2", encoding="utf-8") + b'\x01' + bytes("9="+str(bodyLength), encoding="utf-8") + b'\x01' + login_request

    checkSumStr = getCheckSum(login_request)

    login_request = login_request + bytes("10="+checkSumStr, encoding="utf-8") + b'\x01'

    # login_request = bytes("8=FIX.4.2", encoding="utf-8") + b'\x01' + bytes('9=90', encoding="utf-8")

    return dict(
        type="binary/fix",
        encoding="binary",
        content=login_request,
    )

def getSendingTime():
    return datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]

def getCheckSum(fixMessage):
    checkSum = 0
    for byte in fixMessage:
        checkSum = checkSum + int(byte)
    checkSumStr = str(checkSum % 256)
    return checkSumStr.zfill(3)

def start_connection(host, port):
    addr = (host, port)
    print("starting connection to", addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    # message = fixlibclient.Message(sel, sock, addr, request)
    # sel.register(sock, events, data=message)
    return (sock, events)


if len(sys.argv) != 7:
    print("usage:", sys.argv[0], "<host> <port> <sender_comp_id> <target_comp_id> <send_seq_num> <receive_seq_num>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
sender_comp_id = sys.argv[3]
target_comp_id = sys.argv[4]
send_seq_num = sys.argv[5]
receive_seq_num = sys.argv[6]
request = create_login_request(sender_comp_id, target_comp_id, send_seq_num)
(sock, events) = start_connection(host, port)

# Send login request
addr = (host, port)
message = fixlibclient.Message(sel, sock, addr, request)
sel.register(sock, events, data=message)



try:
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
            except Exception:
                print(
                    "main: error: exception for",
                    f"{message.addr}:\n{traceback.format_exc()}",
                )
                message.close()
        # Check for a socket being monitored to continue
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()
