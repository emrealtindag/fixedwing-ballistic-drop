file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
import re
match = re.search(r'def main\(\).*?(while self\.running:|while True:)(.*)', text, re.DOTALL)
if match:
    print(match.group(2)[:1500])
else:
    print("Loop not found")
