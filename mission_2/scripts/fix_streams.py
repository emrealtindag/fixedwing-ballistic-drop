file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

req_code = """
        logger.info("Connected to MAVLink: %s", mav_cfg["connection_string"])
        # Request data streams to ensure we get telemetry on this specific channel
        try:
            mav_conn.mav.request_data_stream_send(
                mav_conn.target_system, mav_conn.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1
            )
            logger.info("Requested MAVLink data streams at 10Hz")
        except Exception as e:
            logger.error("Failed to request data streams: %s", e)
"""

text = text.replace('logger.info("Connected to MAVLink: %s", mav_cfg["connection_string"])', req_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
