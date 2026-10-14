file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the roll/pitch attribute names
text = text.replace('telemetry.roll.value', 'telemetry.roll_deg.value')
text = text.replace('telemetry.pitch.value', 'telemetry.pitch_deg.value')

# Fix the cap.release() bug for TCP block
cap_fix = """if 'cap' in locals() and hasattr(cap, 'release'):
        cap.release()
    if 'conn' in locals() and hasattr(conn, 'close'):
        conn.close()
    if 'server_sock' in locals() and hasattr(server_sock, 'close'):
        server_sock.close()"""
text = text.replace('cap.release()', cap_fix)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
