file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('(320, 52)', '(320, 52)') # wait, gate_txt is at 320.
text = text.replace('(470, 52)', '(540, 52)') # Move TRACK to the right

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
