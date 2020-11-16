#!/usr/bin/env python3

import sys
from datetime import datetime
import select
import threading

import FixSocketHandler
from FixParser import FixParser


class FixAppServer:

    def __init__(self, fix_server_sock, sender_comp_id, target_comp_id, send_seq_num,):
        self.fix_server_sock = fix_server_sock
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.send_seq_num = send_seq_num
        self.current_seq_num = int(send_seq_num)

    def create_login_response(self):

        login_list = []

        login_list.append(("35", "A"))  # MsgType
        login_list.append(("34", self.send_seq_num))  # MsgSeqNum
        login_list.append(("49", self.sender_comp_id))  # SenderCompID
        login_list.append(("52", self.getSendingTime()))  # SendingTime
        login_list.append(("56", self.target_comp_id))  # TargetCompID
        login_list.append(("98", "0"))  # EncryptMethod
        login_list.append(("108", "30"))  # HeartBeatInt

        login_response = b''
        for login_tag in login_list:
            login_response = login_response + bytes(login_tag[0] + "=" + login_tag[1], encoding="utf-8") + b'\x01'

        bodyLength = len(login_response)  # 9 - BodyLength

        login_response = bytes("8=FIX.4.2", encoding="utf-8") + b'\x01' + bytes("9="+str(bodyLength), encoding="utf-8") + b'\x01' + login_response

        checkSumStr = self.getCheckSum(login_response)

        login_response = login_response + bytes("10="+checkSumStr, encoding="utf-8") + b'\x01'

        self.current_seq_num += 1

        return login_response

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
        self.fix_server_sock.send(heartbeat)
        print(f"Sending Heartbeat to {self.fix_server_sock.sock.getpeername()}: {FixParser.parse_fix_bytes(heartbeat)} ")


if __name__ == "__main__":

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
                    # Receive messages from client
                    fix_client_sock = FixSocketHandler.FixSocketHandler(notified_socket)
                    received_messages = fix_client_sock.receive()

                    for received_message in received_messages:

                        fix_dict = FixParser.parse_fix_bytes(received_message)

                        if fix_dict["35"] == "A":
                            # Found a login request, send a login response
                            print("Received Login Request")
                            sender_comp_id = fix_dict["56"]
                            target_comp_id = fix_dict["49"]

                            # Create FixAppServer object
                            fix_app_server = FixAppServer(fix_client_sock, sender_comp_id, target_comp_id, "1")

                            login_response = fix_app_server.create_login_response()
                            fix_client_sock.send(login_response)
                            print("Sent Login Response")
                            # Start sending Heartbeats
                            fix_app_server.start_sending_heartbeats()

    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        for sock in socket_list:
            sock.close()

























