import socket

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 7000
BUFFER_SIZE = 1024


def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        msg = input("Message (exit to quit): ")
        if msg.lower() == "exit":
            break

        client.sendto(msg.encode(), (SERVER_HOST, SERVER_PORT))
        data, _ = client.recvfrom(BUFFER_SIZE)
        print("Server:", data.decode())

    client.close()


if __name__ == "__main__":
    main()
