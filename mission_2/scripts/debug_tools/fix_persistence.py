file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the broken line
old_line = "ptxt = f\"TRACK: R[{persistence.counts['red']}/3] B[{persistence.counts['blue']}/3]\""
new_line = "ptxt = f\"TRACK: R[{persistence.get_count('red_target')}/3] B[{persistence.get_count('blue_target')}/3]\""
text = text.replace(old_line, new_line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
