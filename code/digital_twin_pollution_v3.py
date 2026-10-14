#!/usr/bin/env python3
"""PlumeTrace digital twin. ROS 2 Jazzy; operational thresholds are PoC-only.

Peak of synthetic field is an observed hotspot PROXY, not inverse dispersion.
Twin requests Nav2 waypoint via /twin_waypoint; safe_navigation owns Nav2 action.
"""
import json
import math
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class DigitalTwin(Node):
    def __init__(self):
        super().__init__('pollution_digital_twin')
        #https://www.gesetze-im-internet.de/ogewv_2016/anlage_7.html
        for key,val in {'alert_nh3_mg_l':0.6,'low_do_mg_l':7.0,
                        'min_alarm_samples':2,'state_period_sec':5.0,'telemetry_timeout_sec':3.0,
                        'sensor_timeout_sec':6.0,'waypoint_timeout_sec':120.0,
                        'arrival_tolerance_m':0.25}.items():
            self.declare_parameter(key,val)
        self.alert=float(self.get_parameter('alert_nh3_mg_l').value)
        self.low_do=float(self.get_parameter('low_do_mg_l').value)
        self.min_alarm=int(self.get_parameter('min_alarm_samples').value)
        self.odom_timeout=float(self.get_parameter('telemetry_timeout_sec').value)
        self.sensor_timeout=float(self.get_parameter('sensor_timeout_sec').value)
        self.waypoint_timeout=float(self.get_parameter('waypoint_timeout_sec').value)
        self.arrival_tolerance=float(self.get_parameter('arrival_tolerance_m').value)
        self.mode='BASELINE_ROUTE'
        self.decision='CONTINUE'
        self.samples=[];self.ids=set();self.peak=None;self.gradient=None
        self.robot={};self.env={};self.last_odom=None;self.last_sensor=None
        self.alarm_streak=0;self.plume_seen=False;self.target=None
        self.target_sent_at=None;self.final_published=False;self.mission_event=None
        self.pub=self.create_publisher(String,'/digital_twin_state',10)
        self.decision_pub=self.create_publisher(String,'/navigation_decision',10)
        self.waypoint_pub=self.create_publisher(String,'/twin_waypoint',10)
        self.create_subscription(String,'/robot_status',self.on_robot,10)
        self.create_subscription(String,'/pollution',self.on_sample,10)
        self.create_subscription(String,'/twin_mission_event',self.on_mission_event,10)
        self.create_timer(float(self.get_parameter('state_period_sec').value),self.tick)
        self.get_logger().info('Digital Twin V3 ready: plume alarm -> Nav2 waypoint -> arrival')

    def emit(self,pub,obj):
        m=String();m.data=json.dumps(obj,allow_nan=False) if not isinstance(obj,str) else obj;pub.publish(m)

    def on_robot(self,msg):
        try: self.robot=json.loads(msg.data);self.last_odom=time.monotonic()
        except (ValueError,TypeError): self.get_logger().warning('Invalid robot telemetry');return

    def on_sample(self,msg):
        if self.mode in ('COMPLETED','FAILED','STOPPED'):return
        try:
            s=json.loads(msg.data);sid=int(s['sample_id']);a=float(s['nh3_n_mg_l']);d=float(s['do_mg_l'])
            x=float(s['x']);y=float(s['y'])
            if not all(math.isfinite(z) for z in (a,d,x,y)) or min(a,d)<0:raise ValueError('invalid values')
        except (KeyError,ValueError,TypeError) as exc:
            self.get_logger().warning(f'Invalid sample: {exc}');return
        if sid in self.ids:return
        self.ids.add(sid);self.last_sensor=time.monotonic()
        if self.samples:
            p=self.samples[-1];delta=math.hypot(x-p['x'],y-p['y'])
            if delta>0.005:self.gradient=(a-float(p['nh3_n_mg_l']))/delta
        self.samples.append(s)
        self.env={'nh3_n_mg_l':a,'do_mg_l':d,'nearest_obstacle_m':self.robot.get('nearest_obstacle_m')}
        if self.peak is None or a>float(self.peak['nh3_n_mg_l']):self.peak=dict(s)
        if a>=self.alert:self.plume_seen=True
        combined_alarm=a>=self.alert and d<self.low_do
        self.alarm_streak=self.alarm_streak+1 if combined_alarm else 0
        self.get_logger().info(f'P{sid}: NH3-N={a:.3f}, DO={d:.2f}, alarm={combined_alarm}, streak={self.alarm_streak}')
        if self.mode=='BASELINE_ROUTE' and self.alarm_streak>=self.min_alarm:
            self.mode='PAUSED_FOR_ANALYSIS';self.decision='PAUSE'
            self.emit(self.decision_pub,'PAUSE')
            # This target is a sampled plume hotspot, NOT an upstream source estimate.
            self.target={'x':float(self.peak['x']),'y':float(self.peak['y']),
                         'frame_id':'odom','tolerance_m':self.arrival_tolerance,
                         'basis':'PEAK_MEASUREMENT_PROXY'}
            self.get_logger().warning('PLUME ALARM: requesting Nav2 toward observed hotspot proxy')
            self.mode='ROUTING_TO_HOTSPOT';self.decision='NAVIGATE'
            self.target_sent_at=time.monotonic()
            self.emit(self.waypoint_pub,self.target)
        elif self.mode=='BASELINE_ROUTE' and self.plume_seen and a == 0.0:
            self.mode='STOPPED';self.decision='STOP';self.emit(self.decision_pub,'STOP')
        self.publish_state(log=self.mode!='BASELINE_ROUTE')

    def on_mission_event(self,msg):
        try:e=json.loads(msg.data)
        except ValueError:return
        self.mission_event=e
        status=e.get('status')
        if self.mode=='ROUTING_TO_HOTSPOT':
            if status=='ARRIVED':
                target=self.target or {};x=self.robot.get('x');y=self.robot.get('y')
                if x is not None and y is not None and math.hypot(float(x)-target['x'],float(y)-target['y'])<=self.arrival_tolerance+0.10:
                    self.mode='COMPLETED';self.decision='STOP'
                    self.get_logger().info('ARRIVAL VERIFIED from Nav2 success + robot odometry')
                else:
                    self.mode='FAILED';self.decision='STOP'
                    self.get_logger().warning('Nav2 arrival reported but odometry outside tolerance')
                self.emit(self.decision_pub,'STOP')
            elif status in ('FAILED','REJECTED','NAV2_UNAVAILABLE','TIMEOUT'):
                self.mode='FAILED';self.decision='STOP';self.emit(self.decision_pub,'STOP')
                self.get_logger().warning(f'Route failed: {e}')
        self.publish_state(log=True)

    def tick(self):
        if self.mode=='ROUTING_TO_HOTSPOT' and self.target_sent_at is not None:
            if time.monotonic()-self.target_sent_at>self.waypoint_timeout:
                self.mode='FAILED';self.decision='STOP';self.emit(self.decision_pub,'STOP')
                self.mission_event={'status':'TIMEOUT','reason':'waypoint timeout'}
        if self.mode in ('COMPLETED','FAILED','STOPPED') and self.final_published:return
        self.publish_state(log=True)
        if self.mode in ('COMPLETED','FAILED','STOPPED'):self.final_published=True

    def publish_state(self,log=False):
        t=time.monotonic()
        robot_age=None if self.last_odom is None else t-self.last_odom
        sensor_age=None if self.last_sensor is None else t-self.last_sensor
        peak=self.peak
        state={'timestamp':self.get_clock().now().nanoseconds/1e9,
               'robot':{k:self.robot.get(k) for k in ('x','y','yaw','velocity_mps','status','battery_percent','battery_voltage_v','battery_source','battery_is_simulated','battery_estimated_remaining_min')},
               'environment':{**self.env,'nearest_obstacle_m':self.robot.get('nearest_obstacle_m')},
               'pollution':{'alarm':self.mode!='BASELINE_ROUTE' and self.plume_seen,
                            'gradient_mg_l_per_m':self.gradient,
                            'estimated_source_x':None,'estimated_source_y':None,
                            'suspected_hotspot_x':peak['x'] if peak else None,
                            'suspected_hotspot_y':peak['y'] if peak else None,
                            'sample_count':len(self.samples),'sensor_origin':'SYNTHETIC_POSITION_BASED',
                            'measurement_accuracy':'NOT_VALIDATED'},
               'synchronization':{'robot_telemetry_fresh':robot_age is not None and robot_age<=self.odom_timeout,
                                  'sensor_data_fresh':sensor_age is not None and sensor_age<=self.sensor_timeout,
                                  'robot_telemetry_age_sec':round(robot_age,2) if robot_age is not None else None,
                                  'sensor_data_age_sec':round(sensor_age,2) if sensor_age is not None else None,
                                  'last_sample_id':self.samples[-1]['sample_id'] if self.samples else None,
                                  'battery_available':self.robot.get('battery_percent') is not None},
               'mission':{'current_target':self.target,'mode':self.mode,'decision':self.decision,
                          'last_nav2_event':self.mission_event}}
        self.emit(self.pub,state)
        if log:self.get_logger().info('Digital Twin state: '+json.dumps(state,allow_nan=False))

def main():
    rclpy.init();node=DigitalTwin()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=='__main__':main()
