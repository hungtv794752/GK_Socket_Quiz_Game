import socket
import threading
import json
import time
import sys

import protocol_message as P

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5555

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# ------------------ shared state ------------------

lock = threading.Lock()

current_qid = None
choices = []
start_time = 0.0
time_limit = 0

mode = "idle"      # idle | question
answered = False


# ------------------ networking ------------------

def send(msg: dict):
    P.validate(msg)
    sock.sendall((json.dumps(msg) + "\n").encode())


def receive_loop():
    buffer = ""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break

            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                msg = json.loads(line)
                P.validate(msg)
                handle_message(msg)

        except Exception as e:
            print("Receive error:", e)
            break

    print("🔌 Disconnected")
    sys.exit()


# ------------------ message handling ------------------

def handle_message(msg: dict):
    global current_qid, choices, start_time, time_limit, mode, answered

    t = msg["type"]

    if t == P.WELCOME:
        print(f"👋 Welcome, {msg['player']}")
        print("Type /start to begin")

    elif t == P.QUESTION:
        with lock:
            current_qid = msg["qid"]
            choices = msg["choices"]
            start_time = msg["server_time"]
            time_limit = msg["time_limit_sec"]
            answered = False
            mode = "question"

        print("\n" + "=" * 40)
        print("📘 QUESTION:", msg["question"])
        for i, c in enumerate(choices):
            print(f"  {chr(65+i)}. {c}")

    elif t == P.ROUND_RESULT:
        with lock:
            mode = "idle"

        print("\n✅ Correct answer:", msg["correct_answer"])
        print("🏆 Winner:", msg["winner"])
        print("📊 Leaderboard:")
        for p in msg["leaderboard"]:
            print(" ", p)

    elif t == P.GAME_OVER:
        print("\n🎉 Game Over!")
        sys.exit()


# ------------------ input loop (ONLY place with input()) ------------------

def input_loop():
    global answered, mode

    while True:
        text = input("> ").strip()

        if text.lower() == "/start":
            send(P.start())
            continue

        with lock:
            if mode != "question" or answered:
                print("❌ No active question")
                continue

            ans = text.upper()
            if ans not in ["A", "B", "C", "D"]:
                print("❌ Invalid choice")
                continue

            answered = True
            elapsed = time.time() - start_time

        print(f"⏱ Answered in {elapsed:.3f}s")

        send(P.answer(
            qid=current_qid,
            answer=choices[ord(ans) - 65]
        ))


# ------------------ main ------------------

sock.connect((SERVER_HOST, SERVER_PORT))

name = input("Enter your name: ").strip()
sock.sendall((name + "\n").encode())

threading.Thread(target=receive_loop, daemon=True).start()

# IMPORTANT: input runs in MAIN THREAD
input_loop()
