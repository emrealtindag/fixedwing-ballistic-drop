import re
file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Eger video source 'udp_jpeg' ise socket uzerinden oku
udp_logic = '''
    if args.video_source == 'udp_jpeg':
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('127.0.0.1', 5600))
        sock.settimeout(2.0)
        logger.info("Listening for Gazebo video on UDP 5600...")
        def get_frame():
            try:
                data, _ = sock.recvfrom(65536)
                np_data = np.frombuffer(data, dtype=np.uint8)
                return True, cv2.imdecode(np_data, cv2.IMREAD_COLOR)
            except:
                return False, None
    else:
        video_source_input = int(args.video_source) if args.video_source.isdigit() else args.video_source
        cap = cv2.VideoCapture(video_source_input)
        if not cap.isOpened():
            logger.error("Failed to open video source: %s", args.video_source)
            sys.exit(1)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        def get_frame():
            return cap.read()
'''

text = re.sub(r'video_source_input = .*?height = int\(cap.get\(cv2.CAP_PROP_FRAME_HEIGHT\)\) or 480', udp_logic, text, flags=re.DOTALL)

# Update the loop to use get_frame
text = text.replace('ret, frame = cap.read()', 'ret, frame = get_frame()')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
