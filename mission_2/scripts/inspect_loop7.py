file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.rfind('get_frame()') # Find the last instance, where it's actually called
print(text[idx-200:idx+1500])
