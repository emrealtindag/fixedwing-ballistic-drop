file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Revert propeller thrust multiplier back to safe limits
text = text.replace('<multiplier>1500</multiplier>', '<multiplier>838</multiplier>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Reverted thrust multiplier to prevent NaN explosion.")
