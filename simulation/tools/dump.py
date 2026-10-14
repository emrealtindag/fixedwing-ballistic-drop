import sys
sys.path.append('/home/emre/ardupilot/Tools/autotest')
from pysim import vehicleinfo
v = vehicleinfo.VehicleInfo()
print(v.options['ArduPlane']['frames']['plane'])
