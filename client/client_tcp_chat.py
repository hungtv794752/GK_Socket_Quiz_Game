import socket
import threading

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
BUFFER_SIZE = 1024


def receive_messages(sock):
    while True:
        try:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                break
            print("\n[Server]:", data.decode())
        except:
            break


def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER_HOST, SERVER_PORT))
    print("✅ Connected to TCP chat server")

    name = input("Enter your name: ")
    client.send(name.encode())

    threading.Thread(
        target=receive_messages,
        args=(client,),
        daemon=True
    ).start()

    try:
        while True:
            msg = input()
            if msg.lower() == "exit":
                break
            client.send(msg.encode())
    finally:
        client.close()
        print("🔌 Disconnected")


if __name__ == "__main__":
    main()
