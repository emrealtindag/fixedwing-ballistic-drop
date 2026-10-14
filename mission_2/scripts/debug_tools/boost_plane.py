file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Boost propeller thrust (multiplier 838 -> 1500)
text = text.replace('<multiplier>838</multiplier>', '<multiplier>1500</multiplier>')

# Boost wing lift area (0.12 -> 0.24) to make it take off easier
text = text.replace('<area>0.12</area>', '<area>0.24</area>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Boosted Thrust and Lift!")
