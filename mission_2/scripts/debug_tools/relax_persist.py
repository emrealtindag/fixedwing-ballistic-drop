file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'persistence_frames = int(mis_cfg.get("persistence_frames", 3))',
    'persistence_frames = 1'
)

with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print("Set persistence to 1.")
