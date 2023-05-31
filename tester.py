import socket
import time


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    address = ("127.0.0.1", 5588)
    frame = bytearray([2, 192, 168, 1, 148, 2, 16])
    s.sendto(frame, address)
    msg = s.recvfrom(1024)
    if(msg != ""):
        print(msg)
    
    