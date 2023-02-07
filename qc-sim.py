import Qubit
import socket as s
import _thread
import random

STATE = 0
Q_PORT = 5870
PC_PORT = 5871
ROUNTRIP_QUBIT_MAX = 64


def get_new_key_as_initiator(req_key_len):
    conn = s.socket(s.AF_INET, s.SOCK_STREAM)
    conn.connect(("127.0.0.1", 5880)) # Port will be set, ip will be a variable from the PC request.

    qubit_measurements = []
    key = ""
    id = ""

    conn.sendall(bytes("gen-" + str(req_key_len)))
    
    while(len(key) < req_key_len):
        data = conn.recv(1024).decode()
        args = data.split("-")

        if(args[0] == "r0"): # Qubit transfer round, then send basis
            basis_str = ""
            for i in range(1, len(args)):
                q = Qubit(args[i])
                basis = random.randint(0,1)
                measurement = q.measure(0 + (45 if basis == 1 else 0))
                qubit_measurements.append((measurement, basis))
                basis_str += str(basis) + "-"
            conn.sendall(bytes("r1-" + basis_str[:-1]))

            
        
        elif(args[0] == "r1"): # Basis receive/check round
            success_count = 0
            for i in range(1, len(args)):
                if(args[i] != qubit_measurements[i][1]):
                    qubit_measurements[i][1] = None
                else:
                    success_count += 1
            success_ratio = success_count / (len(args) - 1)
            if( success_ratio > 0.55 or success_ratio < 0.45):
                conn.sendall(b"f")
                # TODO: Reset variables
                continue
            else:
                pass
                # TODO: Send half our qubits here for testing
            

        elif(args[0] == "r2"): # Test round (give half the qubits) (r2-xy-xy-xy...) -> x: index of qubit. y: expected value of the qubit
            measurement_vals = ""
            for i in range(1, args[1]):
                if(args[i][1] != qubit_measurements[args[i][0]]):
                    conn.sendall(b"f")
                    # TODO: Handle variable resets for restart.
                    continue
                qubit_measurements[args[i][0]] = None

            # This section will be done by the initiated
                #measurement_vals += args[i][0] + qubit_measurements[args[i][0]] + "-"
            #conn.sendall(bytes("r4-" + measurement_vals[:-1]))
            #---------------------------------------------
            conn.sendall(b"r3")

        elif(args[0] == "r3"): # Wrap up
            if(len(args[0]) > 0): # Server will give key ID if the key is generated fully.
                id = args[1]

            for i in range(len(qubit_measurements)):
                if(qubit_measurements[i] != None):
                    key += qubit_measurements[i][0]

            diff = req_key_len - len(key)
            if (diff < 0):
                key = key[:diff] # Removing extra keys if too many were generated.

        elif(args[0] == "f"):
            pass # TODO: Handle variable resets for restart.

        # Initiated will decide if the process will be restarted.
        # When key length is not in the required length, we will not stop listening anyways..
        # ..So it's not necessary to say that we are ready and we are waiting for more.

    return key

def q_server_listen_loop(server):
    conn, address = server.accept()
    while True:
        data = conn.recv(1024).decode()
        print(data)

def pc_server_listen_loop(server):
    conn, address = server.accept()
    while True:
        data = conn.recv(1024).decode()
        if(len(data) != 0):
            args = data.split("-")

            if(args[0] == "key"):
                key_len = int(args[1])
                key, id = get_new_key_as_initiator(key_len) # Might consider making this async so it doesn't block the thread.
                conn.sendall(bytes("keyr-" + key + "-" + id))



print("Booting..")

try:
    q_server = s.socket()
    q_server.bind(('', Q_PORT))
    q_server.listen(1)

    _thread.start_new_thread( q_server_listen_loop, ( q_server, )  )
    print("Quantum server created.")

    pc_server = s.socket()
    pc_server.bind(('', PC_PORT))
    pc_server.listen(1)

    _thread.start_new_thread( pc_server_listen_loop, ( pc_server, )  )
    print("PC server created.")

except s.error as err:
    print("[0] Server creation error:")
    print(err)


while True:
    pass