file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'def\s+(\w+)\s*\(', text)
print(matches)
