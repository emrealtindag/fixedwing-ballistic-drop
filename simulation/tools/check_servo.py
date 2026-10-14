import time
from pymavlink import mavutil

try:
    master = mavutil.mavlink_connection('tcp:127.0.0.1:5777')
    msg = master.wait_heartbeat(timeout=3)
    if msg:
        print('Heartbeat received')
    else:
        print('No heartbeat')
        exit(1)
    
    # Request data stream
    master.mav.request_data_stream_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_RAW_CONTROLLERS, 10, 1)
        
    start_time = time.time()
    while time.time() - start_time < 3:
        msg = master.recv_match(type='SERVO_OUTPUT_RAW', blocking=True, timeout=1)
        if msg:
            print(f'Servo 3 Output: {msg.servo3_raw}')
            break
except Exception as e:
    print(f'Error: {e}')
