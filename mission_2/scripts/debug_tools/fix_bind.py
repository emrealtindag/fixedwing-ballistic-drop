file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("sock.bind(('127.0.0.1', 5600))", "sock.bind(('0.0.0.0', 5600))")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
