import re
file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Restore stale telemetry safety check!
text = text.replace('if False: # telemetry.is_stale() and mav_conn is not None:', 'if telemetry.is_stale() and mav_conn is not None:')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
