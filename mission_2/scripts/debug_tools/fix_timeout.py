file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("server_sock.settimeout(30.0)", "server_sock.settimeout(300.0)  # 5 minutes")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
