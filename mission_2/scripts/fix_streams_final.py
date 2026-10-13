file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

req_code = """        mav_conn = mavutil.mavlink_connection(conn_str)
        try:
            mav_conn.wait_heartbeat(timeout=5)
            mav_conn.mav.request_data_stream_send(
                mav_conn.target_system, mav_conn.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1
            )
            logger.info("Requested streams from ArduPilot")
        except Exception as e:
            pass
"""

text = text.replace('        mav_conn = mavutil.mavlink_connection(conn_str)', req_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
