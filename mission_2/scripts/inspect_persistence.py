file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

class_start = text.find('class PersistenceTracker')
class_end = text.find('class ', class_start + 10)
print(text[class_start:class_end])
