file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

import re
match = re.search(r'try:.*?detector = YOLOTargetDetector.*?except.*?:(.*?)(?=\n\s*\w)', text, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("No try-except block for detector found.")
