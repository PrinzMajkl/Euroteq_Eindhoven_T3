uint8 ORIGIN_REAL=0
uint8 ORIGIN_VIRTUAL=1
uint8 MODE_REROUTE=0
uint8 MODE_STOP=1
string id
uint8 origin
uint8 mode
geometry_msgs/Polygon footprint   # arena frame
float32 height_m
float32 confidence
builtin_interfaces/Time last_seen
