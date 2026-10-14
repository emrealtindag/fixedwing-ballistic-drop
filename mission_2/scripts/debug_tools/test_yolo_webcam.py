import cv2
from ultralytics import YOLO

def main():
    print("--- YOLOv8 WEBCAM TEST ---")
    print("Loading model: best.pt...")
    
    try:
        model = YOLO(r"ai_training\runs\detect\teknofest_iha-2\weights\best.pt")
        print("Model loaded successfully!")
    except Exception as e:
        print(f"ERROR: Could not load model. {e}")
        return

    print("Opening webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        return
        
    print("Webcam is active. Press 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break
            
        # Run YOLO detection (conf=0.25 to make it very sensitive for hand-drawn paper)
        results = model(frame, conf=0.25, verbose=False)
        
        # Draw bounding boxes on the frame
        annotated_frame = results[0].plot()
        
        cv2.imshow("YOLO RAW TEST", annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("Test finished cleanly.")

if __name__ == '__main__':
    main()
