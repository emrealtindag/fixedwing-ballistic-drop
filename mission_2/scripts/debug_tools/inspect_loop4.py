file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('get_frame')
print(text[idx-500:idx+1000])
