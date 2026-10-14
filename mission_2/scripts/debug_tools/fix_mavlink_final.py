file_path = r'mission_2\configs\mission2_fixedwing.yaml'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(r'connection_string:.*', 'connection_string: "tcp:127.0.0.1:5760"', text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
