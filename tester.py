import socket
import time


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    time1 = time.time()
    s.connect(("127.0.0.1", 5588))
    s.sendall(b"key-100-127.0.0.1")
    while(True):
        data = s.recv(1024).decode()
        if(data != ""):
            print(data)
            s.close()
            break
    time2 = time.time()
    print(str(time2 - time1))
    