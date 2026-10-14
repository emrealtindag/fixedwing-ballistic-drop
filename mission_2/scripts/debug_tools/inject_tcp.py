import re
file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the udp_jpeg logic with tcp_jpeg logic
tcp_logic = '''
    if args.video_source == 'udp_jpeg':
        import socket
        import struct
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(('0.0.0.0', 5600))
        server_sock.listen(1)
        server_sock.settimeout(30.0)
        logger.info("Listening for Gazebo video on TCP 5600...")
        conn, addr = server_sock.accept()
        conn.settimeout(2.0)
        logger.info("Connected to Gazebo Video Stream!")
        
        def get_frame():
            try:
                # Read 4 bytes for length
                raw_msglen = b''
                while len(raw_msglen) < 4:
                    packet = conn.recv(4 - len(raw_msglen))
                    if not packet: return False, None
                    raw_msglen += packet
                msglen = struct.unpack('>I', raw_msglen)[0]
                
                # Read image data
                data = b''
                while len(data) < msglen:
                    packet = conn.recv(msglen - len(data))
                    if not packet: return False, None
                    data += packet
                
                np_data = np.frombuffer(data, dtype=np.uint8)
                return True, cv2.imdecode(np_data, cv2.IMREAD_COLOR)
            except Exception as e:
                return False, None
'''

# Find and replace the old UDP block
start_idx = text.find("if args.video_source == 'udp_jpeg':")
end_idx = text.find("else:", start_idx)

if start_idx != -1 and end_idx != -1:
    text = text[:start_idx] + tcp_logic.strip() + "\n    " + text[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
        print("Patched demo_pipeline.py for TCP")
