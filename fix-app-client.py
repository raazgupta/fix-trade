#!/usr/bin/env python3

import sys
from datetime import datetime
import threading

import FixSocketHandler
from FixParser import FixParser

class FixAppClient:

    def __init__(self, fix_client_sock, sender_comp_id, target_comp_id, send_seq_num, receive_seq_num):
        self.fix_client_sock = fix_client_sock
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.send_seq_num = send_seq_num
        self.receive_seq_num = receive_seq_num
        self.current_seq_num = int(send_seq_num)

    def create_login_request(self):

        login_list = []

        login_list.append(("35", "A"))  # MsgType
        login_list.append(("34", self.send_seq_num))  # MsgSeqNum
        login_list.append(("49", self.sender_comp_id))  # SenderCompID
        login_list.append(("52", self.getSendingTime()))  # SendingTime
        login_list.append(("56", self.target_comp_id))  # TargetCompID
        login_list.append(("98", "0"))  # EncryptMethod
        login_list.append(("108", "30"))  # HeartBeatInt
        login_list.append(("141", "N"))  # ResetSeqNumFlag

        login_request = b''
        for login_tag in login_list:
            login_request = login_request + bytes(login_tag[0] + "=" + login_tag[1], encoding="utf-8") + b'\x01'

        bodyLength = len(login_request)  # 9 - BodyLength

        login_request = bytes("8=FIX.4.2", encoding="utf-8") + b'\x01' + bytes("9="+str(bodyLength), encoding="utf-8") + b'\x01' + login_request

        checkSumStr = self.getCheckSum(login_request)

        login_request = login_request + bytes("10="+checkSumStr, encoding="utf-8") + b'\x01'

        self.current_seq_num += 1

        return login_request

    def create_heartbeat_message(self):
        message_list = []

        message_list.append(("35", "0"))  # MsgType
        message_list.append(("34", str(self.current_seq_num)))  # MsgSeqNum
        message_list.append(("49", self.sender_comp_id))  # SenderCompID
        message_list.append(("52", self.getSendingTime()))  # SendingTime
        message_list.append(("56", self.target_comp_id))  # TargetCompID

        message = b''
        for message_tag in message_list:
            message = message + bytes(message_tag[0] + "=" + message_tag[1], encoding="utf-8") + b'\x01'

        body_length = len(message) # 9 - BodyLength

        message = bytes("8=FIX.4.2", encoding="utf-8") + b'\x01' + bytes("9="+str(body_length), encoding="utf-8") + b'\x01' + message

        check_sum_str = self.getCheckSum(message)

        message = message + bytes("10="+check_sum_str, encoding="utf-8") + b'\x01'

        self.current_seq_num += 1

        return message

    def getSendingTime(self):
        return datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]

    def getCheckSum(self, fixMessage):
        checkSum = 0
        for byte in fixMessage:
            checkSum = checkSum + int(byte)
        checkSumStr = str(checkSum % 256)
        return checkSumStr.zfill(3)

    def start_sending_heartbeats(self):

        heartbeat_thread = threading.Timer(30.0, self.start_sending_heartbeats, [])
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        heartbeat = self.create_heartbeat_message()
        self.fix_client_sock.send(heartbeat)


if __name__ == "__main__":
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
    fix_app_client = FixAppClient(fix_client_sock, sender_comp_id, target_comp_id, send_seq_num, receive_seq_num)
    request = fix_app_client.create_login_request()
    print("Sending Login Request:" + str(FixParser.parse_fix_bytes(request)))
    fix_client_sock.send(request)

    # Start sending Heartbeats
    fix_app_client.start_sending_heartbeats()

    try:
        while True:
            input_text = input("new / amend / cancel / receive : ")
            if input_text == "receive":
                received_messages = fix_client_sock.receive()
                if not received_messages:
                    print("No received messages")
                else:
                    for message in received_messages:
                        print(str(FixParser.parse_fix_bytes(message)))

    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        fix_client_sock.close()
