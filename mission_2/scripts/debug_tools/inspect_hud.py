file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'def draw_hud' in line or 'cv2.putText' in line or 'cv2.rectangle' in line:
        print(f"{i}: {line.strip()}")
