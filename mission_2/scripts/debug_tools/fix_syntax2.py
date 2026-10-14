file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('"TEKNOFEST Master Pipeline v2 started.\n', '"TEKNOFEST Master Pipeline v2 started. "\n')
text = text.replace('Frame processing error, skipping frame:\n', 'Frame processing error, skipping frame: %s", frame_exc)\n')
text = text.replace('Telemetry stale; skipping frame.\n', 'Telemetry stale; skipping frame.")\n')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
