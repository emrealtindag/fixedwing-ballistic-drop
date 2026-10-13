file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the gate.is_locked with not gate.is_detection_armed
text = text.replace('gate.is_locked', 'not gate.is_detection_armed')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
