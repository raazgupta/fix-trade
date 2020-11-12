#!/usr/bin/env python3

import socket
import select
import sys


class FixSocketHandler:
    sock: socket.socket
    _begin_string_length: int
    _check_sum_length: int

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._begin_string_length = 10
        self._check_sum_length = 7

    def connect(self, host, port):
        print("starting connection to", (host, port))
        self.sock.connect((host, port))
        self.sock.setblocking(False)

    def close(self):
        print("Closing connection")
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def send(self, message):

        # Wait until the socket is ready to send data
        write_sockets = []
        exception_sockets = []
        while len(write_sockets) == 0 and len(exception_sockets) == 0:
            _, write_sockets, exception_sockets = select.select([], [self.sock], [self.sock])

        if self.sock in exception_sockets:
            # Check if socket in error state
            raise RuntimeError("socket connection broken")
        elif self.sock in write_sockets:
            # Socket is ready to send data
            total_sent = 0
            while total_sent < len(message):
                try:
                    sent = self.sock.send(message[total_sent:])
                    if sent == 0:
                        raise RuntimeError("socket connection broken")
                except Exception as e:
                    print('Writing error: '.format(str(e)))
                    sys.exit()
                total_sent += sent
            return True
        else:
            return False

    def receive(self):
        chunks = []
        received_messages = []

        # Check if the socket has any data to read
        while True:

            try:
                read_sockets, _, exception_sockets = select.select([self.sock], [], [self.sock])

                if self.sock in exception_sockets:
                    # Check if socket in error state
                    raise RuntimeError("socket connection broken")
                elif not read_sockets:
                    # Socket does not have any data left to read
                    return received_messages
                elif self.sock in read_sockets:
                    # Socket has data left to read

                    begin_string_bytes = self.sock.recv(self._begin_string_length)
                    if begin_string_bytes == b'':
                        return received_messages
                    begin_string = begin_string_bytes[:self._begin_string_length - 1].decode("utf-8")
                    if begin_string != "FIX 4.2":
                        print("Not FIX 4.2 message")
                        return received_messages
                    chunks.append(begin_string_bytes)

                    # If it is a FIX message determine the length of the message
                    body_length_bytes = b''
                    received_byte = b''
                    max_potential_message = 2048
                    current_byte_count = 0
                    while received_byte != b'\x01' and current_byte_count <= max_potential_message:
                        received_byte = self.sock.recv(1)
                        current_byte_count += 1
                        body_length_bytes += received_byte
                    body_length_str = body_length_bytes[:len(body_length_bytes) - 1].decode("utf-8")
                    body_length_int = int(body_length_str.split("=")[1])
                    chunks.append(body_length_bytes)

                    # Receive the body and trailing checksum of the message
                    body_bytes = self.sock.recv(body_length_int + self._check_sum_length)
                    chunks.append(body_bytes)

                    received_messages.append(b''.join(chunks))

            except Exception as e:
                print('Reading error: '.format(str(e)))
                sys.exit()
