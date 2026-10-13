file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\aerointel_ws\ros2_udp_bridge.py'
script_content = """import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import socket
import struct
import time

class VideoTransmitter(Node):
    def __init__(self):
        super().__init__('video_transmitter')
        self.subscription = self.create_subscription(
            Image,
            '/downward_camera/image_raw',
            self.image_callback,
            10)
        self.bridge = CvBridge()
        self.target_ip = '172.31.176.1'
        self.sock = None
        self.connect_to_windows()

    def connect_to_windows(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.get_logger().info(f'Connecting to Windows TCP {self.target_ip}:5600...')
        while True:
            try:
                self.sock.connect((self.target_ip, 5600))
                self.get_logger().info('Connected! Streaming Video...')
                break
            except Exception as e:
                time.sleep(1.0)

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
            result, encimg = cv2.imencode('.jpg', cv_image, encode_param)
            if result:
                data = encimg.tobytes()
                self.sock.sendall(struct.pack('>I', len(data)) + data)
        except Exception as e:
            self.get_logger().error('Connection lost, reconnecting...')
            self.connect_to_windows()

def main(args=None):
    rclpy.init(args=args)
    node = VideoTransmitter()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
"""
with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(script_content)
