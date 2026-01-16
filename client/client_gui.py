import socket
import threading
import tkinter as tk

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
BUFFER_SIZE = 1024


class ClientGUI:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((SERVER_HOST, SERVER_PORT))

        self.root = tk.Tk()
        self.root.title("TCP Client Chat")

        self.text = tk.Text(self.root, height=15)
        self.text.pack()

        self.entry = tk.Entry(self.root)
        self.entry.pack(fill=tk.X)
        self.entry.bind("<Return>", self.send_message)

        threading.Thread(
            target=self.receive_messages,
            daemon=True
        ).start()

        self.root.mainloop()

    def send_message(self, event):
        msg = self.entry.get()
        if msg:
            self.sock.send(msg.encode())
            self.entry.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                msg = self.sock.recv(BUFFER_SIZE).decode()
                self.text.insert(tk.END, msg + "\n")
            except:
                break


if __name__ == "__main__":
    ClientGUI()
