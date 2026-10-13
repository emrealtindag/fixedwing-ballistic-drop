file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

start_idx = text.find('def draw_hud(')
print("start_idx:", start_idx)

end_idx = text.find('def ', start_idx + 10)
print("next def idx:", end_idx)
