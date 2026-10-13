file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('logger.info("Listening for Gazebo video on UDP 5600...")', 
                    'logger.info("Listening for Gazebo video on UDP 5600...")\n        width = 640\n        height = 480')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
