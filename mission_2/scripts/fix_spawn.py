file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\worlds\iris_arducopter_runway.world'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '<model name="iris_demo">\n      <include>',
    '<model name="iris_demo">\n      <pose>0 0 0.5 0 0 0</pose>\n      <include>'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Added spawn altitude to prevent ground collision jitter.")
