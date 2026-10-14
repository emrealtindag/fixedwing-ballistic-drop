import os
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot', 'Tools', 'autotest', 'default_params', 'gazebo-zephyr.parm')
with open(path, 'a', encoding='utf-8') as f:
    f.write("\nTHR_FAILSAFE 0\n")
    f.write("THR_FS_VALUE 1100\n")
    f.write("ARMING_REQUIRE 1\n")
    f.write("RC3_MIN 1100\n")
    f.write("SERVO3_MIN 1100\n")
print("Updated gazebo-zephyr.parm")
