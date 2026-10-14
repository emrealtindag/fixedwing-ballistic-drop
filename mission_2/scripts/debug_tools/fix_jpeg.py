file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\aerointel_ws\ros2_udp_bridge.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('cv2.IMWRITE_JPEG_QUALITY), 60]', 'cv2.IMWRITE_JPEG_QUALITY), 95]')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
