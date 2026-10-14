file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
main_start = text.find('def main')
print(text[main_start:main_start+1500])
