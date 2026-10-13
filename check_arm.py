from pymavlink import mavutil
import time
master = mavutil.mavlink_connection('tcp:127.0.0.1:5777')
master.wait_heartbeat(timeout=3)
msg = master.recv_match(type='HEARTBEAT', blocking=True, timeout=3)
if msg:
    armed = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
    print(f"ARMED_STATUS: {bool(armed)}")
else:
    print("NO_HEARTBEAT")
