import time
from pymavlink import mavutil

print("Connecting to TCP 127.0.0.1:5777...")
try:
    master = mavutil.mavlink_connection('tcp:127.0.0.1:5777')
    master.wait_heartbeat(timeout=10)
    print("Heartbeat from system (system %u component %u)" % (master.target_system, master.target_component))
except Exception as e:
    print("Failed: ", e)

print("Connecting to TCP 127.0.0.1:5778...")
try:
    master2 = mavutil.mavlink_connection('tcp:127.0.0.1:5778')
    master2.wait_heartbeat(timeout=10)
    print("Heartbeat from system 2 (system %u component %u)" % (master2.target_system, master2.target_component))
except Exception as e:
    print("Failed: ", e)
