import time
import math
from pymavlink import mavutil

print('Baglaniliyor...')
master = mavutil.mavlink_connection('tcp:127.0.0.1:5777')
master.wait_heartbeat()
print('Heartbeat alindi!')

# AUTO mode = 10
master.mav.set_mode_send(
    master.target_system,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    10) 
time.sleep(1)

master.arducopter_arm()
print('ARMED! İzleniyor...')

start = time.time()
while time.time() - start < 10:
    msg = master.recv_match(type=['ATTITUDE', 'VFR_HUD'], blocking=True, timeout=1)
    if msg:
        if msg.get_type() == 'ATTITUDE':
            pitch_deg = math.degrees(msg.pitch)
            print(f'Pitch: {pitch_deg:.2f} derece')
        elif msg.get_type() == 'VFR_HUD':
            print(f'Speed: {msg.airspeed:.2f} m/s, Alt: {msg.alt:.2f} m')

master.arducopter_disarm()
