import Qubit as qm
import socket as s
import _thread
import random
from PyQt5.QtNetwork import QNetworkInterface # pyqt5 module required!
import time
import configparser
import json

config = configparser.ConfigParser()
config.read("config.ini")

Q_PORT = int(config['ALL']['Q_PORT'])
PC_PORT = int(config['ALL']['PC_PORT'])
ROUNDTRIP_QUBIT_MAX = int(config['ALL']['ROUNDTRIP_QUBIT_MAX'])
SUCCESS_RATIO_UPPER_BOUNT = float(config['ALL']['SUCCESS_RATIO_UPPER_BOUNT'])
SUCCESS_RATIO_LOWER_BOUNT = float(config['ALL']['SUCCESS_RATIO_LOWER_BOUNT'])
INFO_LOGGING = config['ALL']['INFO_LOGGING'] == 'True'
METRICS_LOGGING = config['ALL']['METRICS_LOGGING'] == 'True'

key_id_index = 0
generated_keys = []

def log(msg):
    if(INFO_LOGGING):
        print(msg)

def log_metrics(msg):
    if(METRICS_LOGGING):
        print(msg)


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
            generated_key = generated_key[:key_count_diff] # Removing excess keys if too many were generated.
    return generated_key


def get_new_key_as_initiator(req_key_len, qc_ip):

    conn = s.socket(s.AF_INET, s.SOCK_STREAM)
    conn.connect((qc_ip, Q_PORT))

    basis_bit_arr = []
    generated_key = ""
    
    conn.sendall(bytes_utf8("gen-" + str(req_key_len)))
    
    time_r1_send = None
    time_r1_receive = None
    time_r2_send = None
    time_r2_receive = None
    time_r2_end = None
    
    while(True):
        data = conn.recv(1024).decode()
        args = data.split("-")
        
        if(data != ""):
            log(data)

        if(args[0] == "r0"): # Qubit measurement round
            basis_str = ""
            for i in range(1, len(args)):
                q = qm.Qubit(int(args[i]))
                rnd_basis = random.randint(0,1)
                measurement = q.measure_with_basis(0 if rnd_basis == 0 else 90)
                basis_bit_arr.append((rnd_basis, measurement))
                basis_str += str(rnd_basis) + "-"
            time_r1_send = time.time()
            conn.sendall(bytes_utf8("r1-" + basis_str[:-1]))

        
        elif(args[0] == "r1"): # Basis receive and check round
            time_r1_receive = time.time()
            log_metrics("Time it took for r1 message to be processed by initiated and sent back was '" + str(time_r1_receive - time_r1_send) + "' seconds. (r1 initiated performance)")

            new_measurements, success_ratio = check_basis_and_modify_arr(args, basis_bit_arr)
            basis_bit_arr = new_measurements
            if( success_ratio < SUCCESS_RATIO_LOWER_BOUNT or success_ratio > SUCCESS_RATIO_UPPER_BOUNT):
                log("Bad success ratio: " + str(success_ratio))
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
                    basis_bit_arr[i] = None
                time_r2_send = time.time()
                log_metrics("Time it took for r1 to be processed by initiator was'" + str(time_r2_send - time_r1_receive) + "' seconds. (r1 initiator performance without network)")
                conn.sendall(bytes_utf8("r2-" + qval_msg[:-1]))

        elif(args[0] == "r2"): # Key gen and wrap up
            time_r2_receive = time.time()
            log_metrics("Time it took for r2 to be processed by initiated was'" + str(time_r2_receive - time_r2_send) + "' seconds. (r2 inited performance)")
            new_key = gen_new_key_from_basis_bits_arr(req_key_len, basis_bit_arr, generated_key)
            generated_key = new_key

            if(len(generated_key) < req_key_len):
                basis_bit_arr = []
                conn.sendall(b"r0")
            else:
                break

            time_r2_end = time.time()
            log_metrics("Time it took for r2 wrap up was " + str(time_r2_end - time_r2_receive) + " seconds. (r2 initiator performance without network)")

        elif(args[0] == "f"):
            basis_bit_arr = []
            continue

    return generated_key

def get_new_key_as_initiated(conn, req_key_len):
    
    generated_key = ""
    is_first_loop = True
    basis_bit_arr = []

    while(True):
        if(not is_first_loop):
            data = conn.recv(1024).decode()
            args = data.split("-")
            if(data != ""):
                log(data)

        if(is_first_loop or args[0] == "r0"): # Qubit genration round
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
            if( success_ratio < SUCCESS_RATIO_LOWER_BOUNT or success_ratio > SUCCESS_RATIO_UPPER_BOUNT):
                log("Bad success ratio: " + str(success_ratio))
                conn.sendall(b"f")
                basis_bit_arr = []
                continue
            
            conn.sendall(bytes_utf8("r1-" + basis_msg))

        elif(args[0] == "r2"):
            for i in range(1, len(args)):
                arr_index = int(args[i][:-1])
                basis_val = int(args[i][-1:])
                if(basis_val != basis_bit_arr[arr_index][1]):
                    log("Failed the test: " + str(basis_val) + "==" + str(basis_bit_arr[arr_index][1]) )
                    conn.sendall(b"f")
                    basis_bit_arr = []
                    break
                basis_bit_arr[arr_index] = None

            
            new_key = gen_new_key_from_basis_bits_arr(req_key_len, basis_bit_arr, generated_key)
            generated_key = new_key
            if(len(generated_key) < req_key_len):
                conn.sendall(b"r2")
                basis_bit_arr = []
                continue
            else:
                conn.sendall(bytes_utf8("r2"))
                break

        is_first_loop = False
        
    return generated_key


def bitstring_to_bytes(s):
    return int(s, 2).to_bytes((len(s) + 7) // 8, byteorder='big')


def q_server_listen_loop(server):
    while(True):
        qc_conn, address = server.accept()
        while(True):
            data = qc_conn.recv(1024).decode()
            args = data.split("-")
            if(args[0] == "gen"):
                key = get_new_key_as_initiated(qc_conn, int(args[1]))
                generated_keys.append((address[0], key))
                qc_conn.close()
                break

def pc_server_listen_loop(server):
    while(True):
        data_address = server.recvfrom(1024)
        data = data_address[0]
        address = data_address[1]
        if(len(data) != 0):
            if(data[0] == 0):
                server.sendto(bytearray([1]), address)
            if(data[0] == 1):
                target_ip_str = str(data[1]) + "." + str(data[2]) + "." + str(data[3]) + "." + str(data[4])
                key_len = data[5:6]
                key = get_new_key_as_initiator(key_len, target_ip_str)
                response_bytes = list(bitstring_to_bytes(key))
                response_bytes.insert(0, 0) # TODO: Make status codes work.

                server.sendto(response_bytes, address)
            if(data[0] == 2):
                target_ip_str = str(data[1]) + "." + str(data[2]) + "." + str(data[3]) + "." + str(data[4])
                for i in range(generated_keys):
                    if(generated_keys[i][0] == target_ip_str):
                        key = generated_keys[i][1]
                        response_bytes = list(bitstring_to_bytes(key))
                        response_bytes.insert(0, 0) # TODO: Make status codes work.
                        generated_keys[i] = None
                        server.sendto(response_bytes, address)
                        break



# MAIN EXECUTION #


print("Booting..")


def listen_interface_for_q(address):
    q_server = s.socket()
    q_server.bind((address, Q_PORT))
    q_server.listen(1)

    _thread.start_new_thread( q_server_listen_loop, ( q_server, )  )
    print("Quantum server created for interface IP: " + address)


def start_q_sv():
    all_Addresses = QNetworkInterface.allAddresses() # IPv6 and IPv4 addresses of all interfaces.
    for addr in all_Addresses: 
        if(addr.toIPv4Address()): # IPv4 addresses of all interfaces. (Need to not allow 127.0.0.1 on real infra or it connects to itself)
             _thread.start_new_thread( listen_interface_for_q, ( addr.toString(),) )
    
try:
    pc_server = s.socket(type=s.SOCK_DGRAM)
    pc_server.bind(('', PC_PORT))

    _thread.start_new_thread( pc_server_listen_loop, ( pc_server, )  )
    print("PC server created.")

    #start_q_sv()
   

except s.error as err:
    print("[0] Server creation error:")
    print(err)



while True: # Necessary for the threads to not die.
    pass