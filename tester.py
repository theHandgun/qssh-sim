import socket

s2 = 0
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(("127.0.0.1", 5871))
    s.sendall(b"key-10-127.0.0.1")
    while(True):
        data = s.recv(1024).decode()
        if(data != ""):
            print(data)