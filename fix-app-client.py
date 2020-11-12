#!/usr/bin/env phython3

import sys

import selectors
from datetime import datetime
# import threading

import FixSocketHandler

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

    return login_request

def create_heartbeat_message(sender_comp_id, target_comp_id, current_seq_num):
    message_list = []

    message_list.append(("35", "0"))  # MsgType
    message_list.append(("34", str(current_seq_num)))  # MsgSeqNum
    message_list.append(("49", sender_comp_id))  # SenderCompID
    message_list.append(("52", getSendingTime()))  # SendingTime
    message_list.append(("56", target_comp_id))  # TargetCompID

    message = b''
    for message_tag in message_list:
        message = message + bytes(message_tag[0] + "=" + message_tag[1], encoding="utf-8") + b'\x01'

    body_length = len(message) # 9 - BodyLength

    message = bytes("8=FIX.4.2", encoding="utf-8") + b'\x01' + bytes("9="+str(body_length), encoding="utf-8") + b'\x01' + message

    check_sum_str = getCheckSum(message)

    message = message + bytes("10="+check_sum_str, encoding="utf-8") + b'\x01'

    return message

def getSendingTime():
    return datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]

def getCheckSum(fixMessage):
    checkSum = 0
    for byte in fixMessage:
        checkSum = checkSum + int(byte)
    checkSumStr = str(checkSum % 256)
    return checkSumStr.zfill(3)

def prettyPrintFix(fix_bytes):
    fix_bytes = fix_bytes.replace(b'\x01', b'^')
    return(str(fix_bytes))

"""
def start_sending_heartbeats(current_seq_num):
    # threading.Timer(30.0, start_sending_heartbeats, [sock, current_seq_num]).start()
    heartbeat = create_heartbeat_message(sender_comp_id, target_comp_id, current_seq_num)
    heartbeat_message = fixlibclient.Message(sel, sock, addr, heartbeat)
    sel.modify(sock, events, data=heartbeat_message)
    #sock.send(heartbeat)
    current_seq_num += 1
"""

if len(sys.argv) != 7:
    print("usage:", sys.argv[0], "<host> <port> <sender_comp_id> <target_comp_id> <send_seq_num> <receive_seq_num>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
sender_comp_id = sys.argv[3]
target_comp_id = sys.argv[4]
send_seq_num = sys.argv[5]
receive_seq_num = sys.argv[6]

# Open Connection to FIX Server

fix_client_sock = FixSocketHandler.FixSocketHandler()
fix_client_sock.connect(host, port)

# Login to FIX Server
request = create_login_request(sender_comp_id, target_comp_id, send_seq_num)
print("Sending Login Request:" + prettyPrintFix(request))
fix_client_sock.send(request)

# current_seq_num = int(send_seq_num)
# current_seq_num += 1

# Start sending Heartbeats
# start_sending_heartbeats(current_seq_num)

try:
    while True:
        input_text = input("new / amend / cancel / receive : ")
        if input_text == "receive":
            received_messages = fix_client_sock.receive()
            if not received_messages:
                print("No received messages")
            else:
                for message in received_messages:
                    print(prettyPrintFix(message))

except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    fix_client_sock.close()
