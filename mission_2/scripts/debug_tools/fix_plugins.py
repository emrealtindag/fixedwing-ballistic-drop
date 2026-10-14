import re
file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\skywalker_x8\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Just delete any block from <plugin to </plugin> if it contains ApplyJointForce
text = re.sub(r'<plugin[^>]*?gz::sim::systems::ApplyJointForce.*?</plugin>', '', text, flags=re.DOTALL)
text = re.sub(r'<plugin[^>]*?gz::sim::systems::JointStatePublisher.*?</plugin>', '', text, flags=re.DOTALL)
text = re.sub(r'<plugin[^>]*?gz-sim-joint-state-publisher-system.*?</plugin>', '', text, flags=re.DOTALL)
text = re.sub(r'<plugin[^>]*?gz-sim-apply-joint-force-system.*?</plugin>', '', text, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Removed ApplyJointForce plugins!")
