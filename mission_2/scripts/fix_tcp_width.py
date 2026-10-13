file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("logger.info(\"Connected to Gazebo Video Stream!\")", 
                    "logger.info(\"Connected to Gazebo Video Stream!\")\n        width = 640\n        height = 480")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
