import socket
import time


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    address = ("127.0.0.1", 5588)
    frame = bytearray([1, 192, 168, 1, 1, 0, 9])
    s.sendto(frame, address)
    