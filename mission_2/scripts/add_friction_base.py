import re

file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

friction_xml = """
        <surface>
          <friction>
            <ode>
              <mu>100.0</mu>
              <mu2>50.0</mu2>
            </ode>
          </friction>
        </surface>
"""
if '<friction>' not in text:
    text = re.sub(r'(<collision name="body_collision">[\s\S]*?</geometry>\n)', r'\1' + friction_xml, text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Friction added to base model.")
else:
    print("Friction already exists.")
