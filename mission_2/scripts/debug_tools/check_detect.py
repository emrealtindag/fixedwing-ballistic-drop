file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

import re
match = re.search(r'def \w*detect\w*\(.*?:', text, re.DOTALL)
if match:
    start_idx = match.start()
    print(text[start_idx:start_idx+1000])
else:
    print("No detect method found.")
