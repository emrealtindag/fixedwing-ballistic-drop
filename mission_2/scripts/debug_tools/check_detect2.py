file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.finditer(r'(class\s+VisionProcessor.*?)(?=class\s|$)', text, re.DOTALL)
for m in matches:
    print(m.group(1)[:1500])
