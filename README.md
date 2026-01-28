🧠 Trò Chơi Quiz Nhiều Người Chơi (Socket TCP)

Đây là một trò chơi quiz nhiều người chơi được xây dựng bằng Python TCP Socket theo mô hình Client – Server.

👉 Người dùng CHỈ cần chạy MỘT file duy nhất (init.py).
File này sẽ tự động khởi động server và client phù hợp với chế độ bạn chọn.

📦 Yêu cầu hệ thống

Python 3.9 trở lên

Khuyến nghị chạy trên Windows
(do sử dụng CREATE_NEW_CONSOLE)

Không cần cài thêm thư viện ngoài

▶️ Cách chạy chương trình (QUAN TRỌNG)
✅ Bước 1: Chạy file khởi động

Tại thư mục gốc của project, chạy lệnh:

python init.py


⚠️ KHÔNG chạy server hoặc client riêng lẻ.
Mọi thứ sẽ được tự động xử lý bởi init.py.

🎮 Chọn chế độ chơi

Sau khi chạy init.py, chương trình sẽ hiển thị:

Select mode:
1 - 👤 Human only (timed)
2 - 🤖 Bot only (no timer)
3 - 👤 + 🤖 Mixed (timed)


Nhập 1, 2 hoặc 3 để chọn chế độ.

🧩 Giải thích các chế độ
1️⃣ Người chơi thật (có giới hạn thời gian)

Khởi động server

Mở client cho người chơi thật

Mỗi câu hỏi có giới hạn thời gian

Phù hợp để chơi thủ công

2️⃣ Bot tự động (không giới hạn thời gian)

Khởi động server ở test mode

Mở các client bot tự động trả lời

Không có độ trễ thời gian

Phù hợp để test và debug hệ thống

3️⃣ Người chơi + Bot (chế độ hỗn hợp)

Khởi động server

Mở client cho người chơi thật

Mở thêm bot tham gia cùng

Có giới hạn thời gian, mang tính cạnh tranh

🏗️ Kiến trúc hệ thống

Server

TCP socket server

Hỗ trợ nhiều client cùng lúc (mỗi client một thread)

Quản lý câu hỏi, lượt chơi và tính điểm

Client

Client người chơi (nhập câu trả lời)

Client bot (trả lời tự động)

File init.py

Khởi động server

Khởi động client theo chế độ đã chọn

Mỗi thành phần chạy trong một cửa sổ console riêng

🧠 Công nghệ sử dụng

Python TCP Socket

Đa luồng (Multi-threading)

Mô hình Client – Server

Giao tiếp bằng JSON

🛑 Dừng chương trình

Đóng cửa sổ server để dừng toàn bộ game

Khi tất cả client thoát, game sẽ tự động reset