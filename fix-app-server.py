#!/usr/bin/env python3

import sys
from datetime import datetime
import select

import FixSocketHandler

def create_login_response(sender_comp_id, target_comp_id, send_seq_num):

    login_list = []

    login_list.append(("35", "A"))  # MsgType
    login_list.append(("34", send_seq_num))  # MsgSeqNum
    login_list.append(("49", sender_comp_id))  # SenderCompID
    login_list.append(("52", getSendingTime()))  # SendingTime
    login_list.append(("56", target_comp_id))  # TargetCompID
    login_list.append(("98", "0"))  # EncryptMethod
    login_list.append(("108", "30"))  # HeartBeatInt

    login_response = b''
    for login_tag in login_list:
        login_response = login_response + bytes(login_tag[0] + "=" + login_tag[1], encoding="utf-8") + b'\x01'

    bodyLength = len(login_response)  # 9 - BodyLength

    login_response = bytes("8=FIX.4.2", encoding="utf-8") + b'\x01' + bytes("9="+str(bodyLength), encoding="utf-8") + b'\x01' + login_response

    checkSumStr = getCheckSum(login_response)

    login_response = login_response + bytes("10="+checkSumStr, encoding="utf-8") + b'\x01'

    return login_response

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

def parse_fix_bytes(fix_bytes):
    fix_dict = {}
    chunks = b''

    byte_list = [fix_bytes[i:i+1] for i in range(len(fix_bytes))]
    for chunk in byte_list:
        if chunk == b'\x01':
            # Delimiter signifying chunks has complete tag
            tag_value_string = chunks.decode("utf-8")
            tag_value_list = tag_value_string.split("=")
            fix_dict[tag_value_list[0]] = tag_value_list[1]
            chunks = b''
        else:
            chunks += chunk

    return fix_dict

"""
def start_sending_heartbeats(current_seq_num):
    # threading.Timer(30.0, start_sending_heartbeats, [sock, current_seq_num]).start()
    heartbeat = create_heartbeat_message(sender_comp_id, target_comp_id, current_seq_num)
    heartbeat_message = fixlibclient.Message(sel, sock, addr, heartbeat)
    sel.modify(sock, events, data=heartbeat_message)
    #sock.send(heartbeat)
    current_seq_num += 1
"""

if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])

socket_list = []

# Listen for connections from FIX Client
fix_server_sock = FixSocketHandler.FixSocketHandler()
fix_server_sock.listen(host, port)
socket_list.append(fix_server_sock.sock)

try:
    # Check for incoming messages
    while True:

        read_sockets, _, exception_sockets = select.select(socket_list, [], socket_list, 0)

        for notified_socket in read_sockets:
            # If notified socket is a server socket - new connection, accept it
            if notified_socket == fix_server_sock.sock:
                # Accept new connection
                client_socket, client_address = fix_server_sock.sock.accept()
                print(f"Accepting new connection from {client_address}")
                socket_list.append(client_socket)
            else:
                # Receive login request
                fix_client_sock = FixSocketHandler.FixSocketHandler(notified_socket)
                received_messages = fix_client_sock.receive()

                if received_messages:
                    # Check if first message is login request
                    fix_dict = parse_fix_bytes(received_messages[0])
                    if fix_dict["35"] == "A":
                        # Found a login request, send a login response
                        print("Received Login Request")
                        sender_comp_id = fix_dict["56"]
                        target_comp_id = fix_dict["49"]
                        login_response = create_login_response(sender_comp_id, target_comp_id, "1")
                        fix_client_sock.send(login_response)
                        print("Sent Login Response")

except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    for sock in socket_list:
        sock.close()

























