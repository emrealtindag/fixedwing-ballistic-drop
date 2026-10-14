file_path = r'mission_2\configs\mission2_fixedwing.yaml'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Switch to listening on ALL interfaces for UDP 14551 (the secondary MAVProxy output)
text = text.replace('tcp:127.0.0.1:5760', 'udp:0.0.0.0:14551')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
