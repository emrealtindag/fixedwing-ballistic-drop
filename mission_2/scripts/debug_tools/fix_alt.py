import re

file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('self.altitude_agl = TelemetryField(float(getattr(msg, "alt", self.altitude_agl.value)), now)', '# Removed VFR_HUD alt override to prevent AMSL overriding AGL')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
