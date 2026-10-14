file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')
for i, line in enumerate(lines):
    if 'mavlink_connection' in line:
        for j in range(i-2, i+5):
            print(f"Line {j}: {lines[j]}")
        break
