import socket
import threading
import json
import time
import random

import protocol_message as P

HOST = "127.0.0.1"
PORT = 5555

BOT_COUNT = 5
ANSWER_DELAY = (3.0, 12.0)

# ------------------ shared observer state ------------------

lock = threading.Lock()

current_question = ""
current_choices = []
answers = {}          # bot -> answer


# ------------------ bot worker ------------------

def bot(name, leader=False):
    global current_question, current_choices, answers
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    sock.sendall((name + "\n").encode())

    buffer = ""

    def send(msg):
        sock.sendall((json.dumps(msg) + "\n").encode())

    while True:
        data = sock.recv(4096)
        if not data:
            return

        buffer += data.decode()
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            msg = json.loads(line)
            t = msg["type"]

            if t == P.QUESTION:
                with lock:
                    # only record once
                    if not current_question:
                        current_question = msg["question"]
                        current_choices[:] = msg["choices"]
                        answers.clear()

                time.sleep(random.uniform(*ANSWER_DELAY))
                choice = random.choice(msg["choices"])

                with lock:
                    answers[name] = choice

                send(P.answer(msg["qid"], choice))

            elif t == P.ROUND_RESULT:
                with lock:
                    # leader prints ONE consolidated view
                    if leader:
                        print("\nQ:", current_question)
                        print("Choices:")
                        for c in current_choices:
                            print(f"  - {c}")

                        print("\nAnswers:")
                        for b, a in answers.items():
                            print(f"  [{b}] Ans: {a}")

                        print(
                            f"✔ Correct: {msg['correct_answer']} "
                            f"| Winner: {msg['winner']}"
                        )

                        lb = " | ".join(
                            f"{p['player']}={p['score']}"
                            for p in msg["leaderboard"]
                        )
                        print("🏆 Leaderboard:", lb)

                        # reset for next round
                        answers.clear()
                        current_question = ""
                        current_choices.clear()

            elif t == P.GAME_OVER:
                print(f"[{name}] Game over — waiting for next game...")


# ------------------ launcher ------------------

threads = []

for i in range(BOT_COUNT):
    time.sleep(0.05)  # stagger connections
    t = threading.Thread(
        target=bot,
        args=(f"[BOT] bot{i}", i == 0),
        daemon=True
    )
    t.start()
    threads.append(t)


print(f"🚀 {BOT_COUNT} bots running (single observer view)")

# keep process alive forever
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("🤖 Bots shutting down")

