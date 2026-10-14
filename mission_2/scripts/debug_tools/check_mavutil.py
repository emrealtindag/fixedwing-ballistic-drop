file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')
for i, line in enumerate(lines):
    if 'mavutil.' in line and 'mavlink_connection' not in line:
        print(f"Line {i}: {line}")
