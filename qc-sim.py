import Qubit as qm
import socket as s
import _thread
import random
import math
import copy

STATE = 0
Q_PORT = 5870
PC_PORT = 5871
ROUNDTRIP_QUBIT_MAX = 64

SUCCESS_RATIO_UPPER_BOUNT = 0.8
SUCCESS_RATIO_LOWER_BOUNT = 0.2

key_id_index = 0

generated_keys = []

def bytes_utf8(msg):
    return bytes(msg, "utf-8")

def check_basis_and_modify_arr(args, basis_bit_arr):
    success_count = 0
    for i in range(1, len(args)):
        if(int(args[i]) != basis_bit_arr[i-1][0]):
            basis_bit_arr[i-1] = None
        else:
            success_count += 1
    success_ratio = success_count / (len(args) - 1)
    
    return basis_bit_arr, success_ratio

def gen_new_key_from_basis_bits_arr(req_key_len, basis_bit_arr, generated_key):
    for i in range(len(basis_bit_arr)):
        if(basis_bit_arr[i] != None):
            generated_key += str(basis_bit_arr[i][1])

    if(len(generated_key) >= req_key_len):
        key_count_diff = req_key_len - len(generated_key)
        if (key_count_diff < 0):
            generated_key = generated_key[:key_count_diff] # Removing extra keys if too many were generated.
    return generated_key

def get_new_key_as_initiator(req_key_len, qc_ip):
    conn = s.socket(s.AF_INET, s.SOCK_STREAM)
    conn.connect((qc_ip, 5870))

    basis_bit_arr = []
    generated_key = ""
    key_id = ""

    conn.sendall(bytes_utf8("gen-" + str(req_key_len)))
    
    while(True):
        data = conn.recv(1024).decode()
        args = data.split("-")
        
        if(data != ""):
            print(data)

        if(args[0] == "r0"): # Qubit transfer round, then send basis
            basis_str = ""
            for i in range(1, len(args)):
                q = qm.Qubit(int(args[i]))
                rnd_basis = random.randint(0,1)
                measurement = q.measure_with_basis(0 if rnd_basis == 0 else 90)
                basis_bit_arr.append((rnd_basis, measurement))
                basis_str += str(rnd_basis) + "-"
            conn.sendall(bytes_utf8("r1-" + basis_str[:-1]))

        
        elif(args[0] == "r1"): # Basis receive/check round
            new_measurements, success_ratio = check_basis_and_modify_arr(args, basis_bit_arr)
            basis_bit_arr = new_measurements
            if( success_ratio < SUCCESS_RATIO_LOWER_BOUNT or success_ratio > SUCCESS_RATIO_UPPER_BOUNT):
                print("Bad success ratio: " + str(success_ratio))
                conn.sendall(b"f")
                basis_bit_arr = []
                continue
            else:
                qval_msg = ""
                for i in range(len(basis_bit_arr)):
                    if(basis_bit_arr[i] == None):
                        continue

                    rnd = random.randint(0,1)

                    if(rnd == 0):
                        continue

                    qval_msg += str(i) +  str(basis_bit_arr[i][1]) + "-"
                
                conn.sendall(bytes_utf8("r2-" + qval_msg[:-1]))
            

        elif(args[0] == "r2"):
            for i in range(1, len(args)):
                #TODO: Remove duplicate code.
                arr_index = int(args[i][:-1])
                basis_val = int(args[i][-1:])
                if(basis_val != basis_bit_arr[arr_index][1]):
                    conn.sendall(b"f")
                    basis_bit_arr = []
                    continue
                basis_bit_arr[arr_index] = None
            
            conn.sendall(b"r3")

        elif(args[0] == "r3"): # Wrap up
            new_key = gen_new_key_from_basis_bits_arr(req_key_len, basis_bit_arr, generated_key)
            generated_key = new_key
            if(len(generated_key) < req_key_len):
                basis_bit_arr = []
                conn.sendall(b"r0")
            else:
                key_id = args[1] # Server will give key ID if the key is generated fully.
                break

        elif(args[0] == "f"):
            basis_bit_arr = []
            continue

    return key_id, generated_key

def get_new_key_as_initiated(conn, req_key_len):
    global key_id_index
    
    key_id = str(key_id_index)
    generated_key = ""
    is_first_loop = True
    basis_bit_arr = []

    key_id_index += 1

    while(True):
        if(not is_first_loop):
            data = conn.recv(1024).decode()
            args = data.split("-")
            if(data != ""):
                print(data)

        if(is_first_loop or args[0] == "r0"):
            round_qubit_len = min(req_key_len*4, ROUNDTRIP_QUBIT_MAX)
            response_msg = ""
            for _ in range(round_qubit_len):
                rnd_bit = random.randint(0,1)
                rnd_basis = random.randint(0,1)
                basis_bit_arr.append((rnd_basis, rnd_bit))

                q_angle = (0 if rnd_bit == 0 else 180) + (0 if rnd_basis == 0 else 90)
                response_msg += str(q_angle) + "-"
            conn.sendall(bytes_utf8("r0-" + response_msg[:-1]))

        elif(args[0] == "r1"):
            basis_msg = ""
            for i in range(len(basis_bit_arr)):
                basis_msg += str(basis_bit_arr[i][0]) + "-"
            basis_msg = basis_msg[:-1]

            new_measurements, success_ratio = check_basis_and_modify_arr(args, basis_bit_arr)
            basis_bit_arr = new_measurements
            # TODO: Remove duplicate code.
            if( success_ratio < SUCCESS_RATIO_LOWER_BOUNT or success_ratio > SUCCESS_RATIO_UPPER_BOUNT):
                print("Bad success ratio:" + str(success_ratio))
                conn.sendall(b"f")
                basis_bit_arr = []
                continue
            
            conn.sendall(bytes_utf8("r1-" + basis_msg))

        elif(args[0] == "r2"):
            is_round_success = True
            basis_bit_vals = ""
            for i in range(1, len(args)):
                #TODO: Remove duplicate code.
                arr_index = int(args[i][:-1])
                basis_val = int(args[i][-1:])
                if(basis_val != basis_bit_arr[arr_index][1]):
                    print("Failed the test: " + str(basis_val) + "==" + str(basis_bit_arr[arr_index][1]) )
                    conn.sendall(b"f")
                    basis_bit_arr = []
                    is_round_success = False
                    break
                basis_bit_vals += str(arr_index) + str(basis_bit_arr[arr_index][1]) + "-"
                basis_bit_arr[arr_index] = None

            if(is_round_success == False):
                break
            conn.sendall(bytes_utf8("r2-" + basis_bit_vals[:-1]))


        elif(args[0] == "r3"):
            new_key = gen_new_key_from_basis_bits_arr(req_key_len, basis_bit_arr, generated_key)
            generated_key = new_key
            if(len(generated_key) < req_key_len):
                conn.sendall(b"r3")
                basis_bit_arr = []
                continue
            else:
                conn.sendall(bytes_utf8("r3-" + key_id))
                break
            

        is_first_loop = False
        
    return key_id, generated_key



def q_server_listen_loop(server):
    while(True):
        qc_conn, address = server.accept()
        # TODO: Only allow whitelisted IP address.
        # This is the connection from quantum channel.
        while(True):
            data = qc_conn.recv(1024).decode()
            args = data.split("-")
            if(args[0] == "gen"):
                id, key = get_new_key_as_initiated(qc_conn, int(args[1]))
                generated_keys.append((id, key))
                qc_conn.close()
                break

def pc_server_listen_loop(server):
    while(True):
        pc_conn, address = server.accept()

        while(True):
            data = pc_conn.recv(1024).decode()
            args = data.split("-")

            if(args[0] == "key"):
                key_len = int(args[1])
                qc_ip = args[2]
                id, key = get_new_key_as_initiator(key_len, qc_ip)
                pc_conn.sendall(bytes_utf8("key-" + key + "-" + id))
                pc_conn.close()
                break



print("Booting..")


# DEBUG
def start_q_sv():
    q_server = s.socket()
    q_server.bind(('', Q_PORT))
    q_server.listen(1)

    _thread.start_new_thread( q_server_listen_loop, ( q_server, )  )
    print("Quantum server created.")

#---------------


try:

    pc_server = s.socket()
    pc_server.bind(('', PC_PORT))
    pc_server.listen(1)

    _thread.start_new_thread( pc_server_listen_loop, ( pc_server, )  )
    print("PC server created.")

    start_q_sv()

   

except s.error as err:
    print("[0] Server creation error:")
    print(err)




while True:
    pass