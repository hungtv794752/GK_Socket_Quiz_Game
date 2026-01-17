# server_socket.py
import socket
import threading
import json
import time
from quiz_logic import QuizGame

HOST = "0.0.0.0"
PORT = 9200

lock = threading.Lock()

clients = {}  # sock -> {"name": str, "role": "player"/"watcher"}
name_to_sock = {}

current_q = None  # payload question hiện tại
game = QuizGame("questions.json")


def send_json(sock: socket.socket, obj: dict):
    data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(data)


def broadcast(obj: dict):
    dead = []
    for s in list(clients.keys()):
        try:
            send_json(s, obj)
        except Exception:
            dead.append(s)
    for s in dead:
        remove_client(s)


def remove_client(sock):
    info = clients.pop(sock, None)
    if info:
        name_to_sock.pop(info.get("name"), None)
    try:
        sock.close()
    except Exception:
        pass


def recv_lines(sock: socket.socket):
    buf = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if line:
                yield line.decode("utf-8", errors="ignore")


def handle_client(sock: socket.socket, addr):
    try:
        send_json(sock, {"type": "hello", "msg": "Send join: {name, role=player|watcher}"})

        for line in recv_lines(sock):
            msg = json.loads(line)

            if msg.get("type") == "join":
                name = (msg.get("name") or "").strip()
                role = (msg.get("role") or "player").strip().lower()
                if role not in ("player", "watcher"):
                    role = "player"

                if not name:
                    send_json(sock, {"type": "join_ack", "ok": False, "reason": "empty_name"})
                    continue

                with lock:
                    # name trùng thì từ chối
                    if name in name_to_sock:
                        send_json(sock, {"type": "join_ack", "ok": False, "reason": "name_taken"})
                        continue
                    clients[sock] = {"name": name, "role": role}
                    name_to_sock[name] = sock

                send_json(sock, {"type": "join_ack", "ok": True, "name": name, "role": role})

                # nếu đang có câu hỏi hiện tại thì gửi lại để người mới vào cũng thấy
                with lock:
                    if current_q:
                        send_json(sock, current_q)

            elif msg.get("type") == "answer":
                # {type:"answer", name:"SV01", qid:"q1", answer:"TCP"}
                name = (msg.get("name") or "").strip()
                qid = msg.get("qid")
                ans = msg.get("answer")

                with lock:
                    info = clients.get(sock)
                    if not info:
                        send_json(sock, {"type": "answer_ack", "ok": False, "reason": "not_joined"})
                        continue

                    if info["role"] != "player":
                        send_json(sock, {"type": "answer_ack", "ok": False, "reason": "watcher_cannot_answer"})
                        continue

                # gọi quiz_logic
                ack = game.submit_answer(name, qid, ans)
                send_json(sock, ack)

            elif msg.get("type") == "ping":
                send_json(sock, {"type": "pong", "t": time.time()})

    except Exception as e:
        # có lỗi thì disconnect
        # print("client error", addr, e)
        pass
    finally:
        with lock:
            remove_client(sock)
        # print("disconnect", addr)


def round_loop():
    global current_q
    while True:
        with lock:
            # chỉ bắt đầu round khi có ít nhất 1 player
            any_player = any(info["role"] == "player" for info in clients.values())

        if not any_player:
            time.sleep(0.5)
            continue

        if not game.has_next_question():
            broadcast({"type": "game_over", "leaderboard": game.get_leaderboard()})
            time.sleep(2)
            continue

        with lock:
            current_q = game.start_round()

        broadcast(current_q)

        # chờ hết time_limit
        time.sleep(game.time_limit_sec)

        # chấm điểm + broadcast kết quả
        result = game.end_round_and_score()
        broadcast(result)

        # nghỉ 2 giây giữa các câu
        with lock:
            current_q = None
        time.sleep(2)


def main():
    # thread chạy vòng game
    t = threading.Thread(target=round_loop, daemon=True)
    t.start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(50)
    print(f"Quiz Server listening on {HOST}:{PORT}")

    while True:
        sock, addr = server.accept()
        threading.Thread(target=handle_client, args=(sock, addr), daemon=True).start()


if __name__ == "__main__":
    main()

