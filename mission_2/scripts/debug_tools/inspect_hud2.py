file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

start_idx = text.find('def draw_hud')
end_idx = text.find('def process_frame', start_idx)
print(text[start_idx:start_idx+1000]) # Print signature and start
