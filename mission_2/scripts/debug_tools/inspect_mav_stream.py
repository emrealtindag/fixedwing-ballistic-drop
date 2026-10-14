file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('mav_conn.mav.request_data_stream_send')
if idx != -1:
    print("Found request_data_stream:", text[idx-50:idx+200])
else:
    print("Not found request_data_stream")
