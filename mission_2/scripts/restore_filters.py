import re

file_path = r'mission_2\src\scandium\perception\target_detector.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Restore confidence filter
text = text.replace('if conf < 0.20: # [TEST BYPASS]: self.conf_threshold yerine 0.20 yapildi', 'if conf < self.conf_threshold:')

# Restore area filter
text = text.replace('# (Area check removed for testing)', 'if area < 400:\n                continue')

# Restore aspect ratio filter
text = text.replace('# (Aspect ratio check removed for testing)', 'if not (0.80 <= aspect <= 1.20):\n                continue')

# Revert the hardcoded conf in predict back to using self.conf_threshold (or slightly below it for safety)
text = text.replace('results = self.model.predict(frame, conf=0.20, verbose=False)', 'results = self.model.predict(frame, conf=self.conf_threshold, verbose=False)')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
