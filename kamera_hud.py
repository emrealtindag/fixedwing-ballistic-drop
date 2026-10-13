#!/usr/bin/env python3
import rospy
import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

def image_callback(msg):
    bridge = CvBridge()
    try:
        # ROS imajını OpenCV formatına çevir
        cv_image = bridge.imgmsg_to_cv2(msg, "bgr8")
        
        # Basit bir HUD cizgisi (hedefgah) ekleyelim
        h, w = cv_image.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # Hedefgah (Crosshair)
        cv2.line(cv_image, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
        cv2.line(cv_image, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)
        
        # Yazi
        cv2.putText(cv_image, "TECHPOD UAV HUD", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow("IHA Kamera HUD", cv_image)
        cv2.waitKey(1)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    rospy.init_node('hud_kamera_izleyici')
    print("HUD Ekranı başlatıldı. Kamera verisi bekleniyor...")
    rospy.Subscriber("/camera/image_raw", Image, image_callback)
    rospy.spin()
