import subprocess
import sys
import time

CREATE_NEW_CONSOLE = subprocess.CREATE_NEW_CONSOLE
PY = sys.executable


print("""
Select mode:
1 - 👤 Human only (timed)
2 - 🤖 Bot only (no timer)
3 - 👤 + 🤖 Mixed (timed)
""")

mode = input("Enter choice: ").strip()

def run(script, *args):
    subprocess.Popen(
        [PY, script, *args],
        creationflags=CREATE_NEW_CONSOLE
    )

# start server with correct mode
if mode == "2":  # bot-only
    run("-m", "server.server", "--test")
else:
    run("-m", "server.server")


time.sleep(0.5)

if mode == "1":
    run("-m", "client.client_tcp_chat")


elif mode == "2":
    run("-m", "client.fake_client_test")

elif mode == "3":
    run("-m", "client.client_tcp_chat")

    time.sleep(0.5)
    run("-m", "client.fake_client_player")

print("🚀 Game launched")
