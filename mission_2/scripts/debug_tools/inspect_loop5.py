file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('while True:')
print(text[idx:idx+1500])
