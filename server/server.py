import socket
import threading
import json
import protocol.message as message
import quiz_logic

HOST = '0.0.0.0'
PORT = 5555

clients = []
lock = threading.Lock()

def broadcast(msg_dict):
    msg = json.dumps(msg_dict).encode()
    with lock:
        for client in clients:
            try:
                client.sendall(msg)
            except:
                clients.remove(client)

def handle_client(client_socket, addr):
    print(f"[+] Client connected: {addr}")
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break

            msg = json.loads(data.decode())
            print(f"[FROM {addr}] {msg}")

            response = quiz_logic.handle_message(msg)
            client_socket.sendall(json.dumps(response).encode())
    except Exception as e:
        print(f"[!] Error with {addr}: {e}")
    finally:
        with lock:
            if client_socket in clients:
                clients.remove(client_socket)
        client_socket.close()
        print(f"[-] Client disconnected: {addr}")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server listening on {HOST}:{PORT}")

    while True:
        client_socket, addr = server.accept()
        with lock:
            clients.append(client_socket)

        thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        thread.start()

if __name__ == "__main__":
    start_server()
