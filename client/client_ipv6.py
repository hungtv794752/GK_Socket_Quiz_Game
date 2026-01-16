import socket

SERVER_HOST = "::1"
SERVER_PORT = 9001
BUFFER_SIZE = 1024


def main():
    client = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    client.connect((SERVER_HOST, SERVER_PORT))
    print("✅ Connected to IPv6 server")

    while True:
        msg = input("Message (exit to quit): ")
        if msg.lower() == "exit":
            break

        client.send(msg.encode())
        data = client.recv(BUFFER_SIZE)
        print("Server:", data.decode())

    client.close()


if __name__ == "__main__":
    main()
