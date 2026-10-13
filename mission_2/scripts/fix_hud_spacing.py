import re

file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix Row 1 coordinates
text = text.replace('(15, 25)', '(30, 35)')
text = text.replace('(160, 25)', '(350, 35)')
text = text.replace('(320, 25)', '(670, 35)')
text = text.replace('(470, 25)', '(1000, 35)')

# Fix Row 2 coordinates
text = text.replace('(15, 52)', '(30, 75)')
text = text.replace('(160, 52)', '(350, 75)')
text = text.replace('(320, 52)', '(670, 75)')
text = text.replace('(540, 52)', '(1000, 75)')
text = text.replace('(470, 52)', '(1000, 75)') # Just in case

# Fix the Top and Bottom dark overlays for 720p
# original: (w, 65) -> now maybe (w, 90)
text = text.replace('(w, 65)', '(w, 100)')
text = text.replace('(w, h - 45)', '(w, h - 60)')

# Fix Payload slots
# Original draw_slot(15, h - 35, "PL-1 [RED]", p1_done)
# Original draw_slot(400, h - 35, "PL-2 [BLU]", p2_done)
text = text.replace('(15, h - 35', '(30, h - 45')
text = text.replace('(400, h - 35', '(950, h - 45')

# Make the boxes bigger inside draw_slot
# cv2.rectangle(frame, (x, y), (x + 200, y + 25), color, 1)
text = text.replace('(x + 200, y + 25)', '(x + 250, y + 35)')
text = text.replace('(x + 5, y + 25)', '(x + 8, y + 35)')

# Make the payload text position fit the bigger box
# cv2.putText(frame, f"{label} : {status}", (x + 15, y + 17)
text = text.replace('(x + 15, y + 17)', '(x + 20, y + 25)')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
