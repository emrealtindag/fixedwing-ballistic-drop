file_path = r'mission_2\configs\mission2_fixedwing.yaml'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('tcp:127.0.0.1:5762', 'tcp:127.0.0.1:5760')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
