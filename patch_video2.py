filepath = r'mission_2\scripts\demo_pipeline.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re
pattern = re.compile(r"    if args\.video_source == 'udp_jpeg':.*?Connected to Gazebo Video Stream!\"", re.DOTALL)

new_block = """    if args.video_source == 'udp_jpeg':
        import socket
        import struct
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.info("Connecting to Gazebo video on TCP 127.0.0.1:5600...")
        import time
        while True:
            try:
                conn.connect(('127.0.0.1', 5600))
                logger.info("Video source connected!")
                break
            except Exception:
                time.sleep(1)"""

content = pattern.sub(new_block, content)
with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
