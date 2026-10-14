file_path = r'mission_2\src\scandium\perception\target_detector.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'if not (0.80 <= aspect <= 1.20):\n                continue',
    'if not (0.50 <= aspect <= 2.00):\n                continue'
)
text = text.replace(
    'area = w * h\n            if area < 400:\n                continue',
    'area = w * h\n            if area < 50:\n                continue'
)

with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print("Relaxed thresholds.")
