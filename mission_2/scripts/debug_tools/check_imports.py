file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
lines = text.split('\n')
for i in range(50):
    print(lines[i])
