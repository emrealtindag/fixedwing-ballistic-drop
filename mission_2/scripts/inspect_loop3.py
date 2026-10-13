file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
loop_start = text.find('try:')
print(text[loop_start:loop_start+2000])
