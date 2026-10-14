file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'is_in_drop_zone = abs(lat_err) <= combined_tol_m and -1.5 <= lon_err <= 1.5',
    'is_in_drop_zone = dist_err <= combined_tol_m'
)
text = text.replace(
    'max_pitch_gate_deg = float(mis_cfg.get("max_pitch_gate_deg", 10.0))',
    'max_pitch_gate_deg = float(mis_cfg.get("max_pitch_gate_deg", 45.0))'
)

with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print("Relaxed drop conditions.")
