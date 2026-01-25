# server.py
import socket
import threading
import json
import sys

from server.quiz_logic import QuizGame
import protocol_message as P

HOST = "0.0.0.0"
PORT = 5555
TEST_MODE = "--test" in sys.argv  # 👈 turn ON for bot tests



game = QuizGame("server/questions.json")
clients = {}          # sock -> player_name
lock = threading.Lock()
game_started = False

# ------------------ networking helpers ------------------

def send(sock, msg):
    P.validate(msg)
    sock.sendall((json.dumps(msg) + "\n").encode())



def broadcast(msg: dict):
    with lock:
        for sock in list(clients.keys()):
            try:
                send(sock, msg)
            except:
                sock.close()
                clients.pop(sock, None)


# ------------------ quiz loop ------------------

def start_quiz_loop_if_needed():
    global game_started

    with lock:
        if game.running or not game_started:
            return
        print("▶ Quiz loop started")
        game.running = True
        threading.Thread(target=quiz_loop, daemon=True).start()


def quiz_loop():

    QUESTION_WAIT = 0.5 if TEST_MODE else game.time_limit_sec
    RESULT_WAIT = 0.3 if TEST_MODE else 3

    while True:
        with lock:
            if not clients:
                print("⏸ No players, stopping quiz")
                game.running = False
                return

        if not game.has_next_question():
            broadcast(P.game_over())
            game.running = False
            return

        q = game.start_round()
        
        if TEST_MODE:
            q["time_limit_sec"] = 1

        broadcast(q)

        threading.Event().wait(QUESTION_WAIT)


        result = game.end_round_and_score()
        broadcast(result)

        threading.Event().wait(RESULT_WAIT)



# ------------------ client handler ------------------

def handle_client(sock, addr):
    global game_started

    print(f"[+] {addr} connected")

    buffer = ""
    name = None

    try:
        name = sock.recv(1024).decode().split("\n", 1)[0].strip()
        if not name:
            return

        with lock:
            clients[sock] = name

        print(f"    Player: {name}")
        send(sock, P.welcome(name))

        while True:
            data = sock.recv(4096)
            if not data:
                break

            buffer += data.decode()

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                msg = json.loads(line)
                P.validate(msg)

                print(f"[{name}] {msg}")

                if msg["type"] == P.ANSWER:
                    resp = game.submit_answer(
                        player=name,
                        qid=msg["qid"],
                        answer=msg["answer"]
                    )
                    send(sock, resp)

                elif msg["type"] == P.START:
                    start = False
                    with lock:
                        if not game_started:
                            print(f"🚀 Game started by {name}")
                            game_started = True
                            start = True

                    if start:
                        start_quiz_loop_if_needed()



    except Exception as e:
        print("Error:", e)

    finally:
        with lock:
            clients.pop(sock, None)

            if not clients:
                print("🔄 All players left — resetting game")
                game.reset()
                game_started = False

        sock.close()
        print(f"[-] {addr} disconnected")


# ------------------ server ------------------

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server listening on {HOST}:{PORT}")

    while True:
        sock, addr = server.accept()
        threading.Thread(
            target=handle_client,
            args=(sock, addr),
            daemon=True
        ).start()


if __name__ == "__main__":
    start()
