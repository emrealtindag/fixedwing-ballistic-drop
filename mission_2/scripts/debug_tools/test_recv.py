import socket, struct, cv2, numpy as np
import time

def test_bridge():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 5600))
    server.listen(1)
    print("Waiting for bridge...")
    server.settimeout(10.0)
    try:
        conn, addr = server.accept()
        print("Connected from", addr)
        conn.settimeout(5.0)
        
        # Read length
        lengthbuf = conn.recv(4)
        if not lengthbuf:
            print("No length buf")
            return
        length = struct.unpack('>I', lengthbuf)[0]
        print("Got frame length:", length)
        
        # Read data
        databuf = b''
        while len(databuf) < length:
            packet = conn.recv(length - len(databuf))
            if not packet:
                break
            databuf += packet
            
        print("Got databuf len:", len(databuf))
        frame = cv2.imdecode(np.frombuffer(databuf, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            print("Successfully decoded frame of shape:", frame.shape)
            mean_val = np.mean(frame)
            print("Frame mean pixel value:", mean_val)
        else:
            print("Failed to decode frame!")
            
    except Exception as e:
        print("Error:", e)
    finally:
        server.close()

test_bridge()
