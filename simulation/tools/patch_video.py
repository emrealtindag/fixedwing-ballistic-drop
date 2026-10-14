filepath = r'mission_2\scripts\demo_pipeline.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """    if args.video_source == 'udp_jpeg':
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(('0.0.0.0', 5600))
        server_sock.listen(1)
        logger.info("Listening for Gazebo video on TCP 5600...")
        conn, addr = server_sock.accept()
        logger.info("Video source connected: %s", addr)"""

new_block = """    if args.video_source == 'udp_jpeg':
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

content = content.replace(old_block, new_block)
with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
