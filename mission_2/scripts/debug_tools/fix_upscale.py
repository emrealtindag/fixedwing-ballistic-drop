file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace "break" with "break\n\n            frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_CUBIC)"
old_block = """logger.info("Video ak sonland veya frames okunamad.")
                break"""
new_block = """logger.info("Video ak sonland veya frames okunamad.")
                break
            
            # Upscale image for HD HUD rendering
            frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_CUBIC)"""

text = text.replace(old_block, new_block)

# Also need to update w, h if it relies on frame.shape?
# `draw_hud` reads `h, w = frame.shape[:2]` so it will dynamically adapt perfectly to 1280x720!
# But wait, my hardcoded crosshair and HUD sizes might look too small on 1280x720?
# Let's adjust FONT_HERSHEY_SIMPLEX scales in draw_hud from 0.55 to 0.75, and thickness from 1/2 to 2.
text = text.replace('0.55', '0.75').replace('0.45', '0.65').replace('cv2.LINE_AA)', '2, cv2.LINE_AA)').replace('1, 2, cv2.LINE_AA)', '2, cv2.LINE_AA)').replace('2, 2, cv2.LINE_AA)', '2, cv2.LINE_AA)')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
