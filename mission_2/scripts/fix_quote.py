with open(r'mission_2\src\scandium\perception\target_detector.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('def _OLD_extract_boxes_from_result(self, res):\n\n        The Ultralytics', 'def _OLD_extract_boxes_from_result(self, res):\n        \"\"\"\n        The Ultralytics')

with open(r'mission_2\src\scandium\perception\target_detector.py', 'w', encoding='utf-8') as f:
    f.write(text)
