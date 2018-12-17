# -*- coding: utf-8 -*-
import ssl
import json
import time

import rospy
from geometry_msgs.msg import Twist

import paho.mqtt.client as mqtt


class AWSIoT(object):
    QOS = 1
    HZ = 10
    
    def __init__(self):
        rospy.loginfo("AWSIot#__init__")
        self.is_connected = False
        self.__client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.__client.on_connect = self._on_connect
        self.__client.on_message = self._on_message
        rospy.on_shutdown(self._on_shutdown)
        self.__params = rospy.get_param("~awsiot")
        
    def run(self):
        rospy.loginfo("AWSIoT#run")
        
        self.__client.tls_set(
            ca_certs=self.__params["certs"]["rootCA"],
            certfile=self.__params["certs"]["certificate"],
            keyfile=self.__params["certs"]["private"],
            tls_version=ssl.PROTOCOL_TLSv1_2)
        
        self.__client.connect(
            self.__params["endpoint"]["host"],
            self.__params["endpoint"]["port"],
            keepalive=120)
        self.__client.loop_start()
        
    def _on_connect(self, client, userdata, flags, response_code):
        rospy.loginfo("AWSIoT#_on_connect response={}".format(response_code))
        client.subscribe(self.__params["mqtt"]["topic"]["sub"], qos=AWSIoT.QOS)
        self.is_connected = True
        self.__cmd_pub = rospy.Publisher("/cmd_vel", Twist, queue_size=1)
        
    def _on_message(self, client, userdata, data):
        topic = data.topic
        payload = str(data.payload)
        rospy.loginfo("AWSIoT#_on_message payload={}".format(payload))
        twist = Twist()
        try:
            params = json.loads(payload)
            if "x" in params and "z" in params and "sec" in params:
                start_time = time.time()
                d = float(params["sec"])
                r = rospy.Rate(AWSIoT.HZ)
                while time.time() - start_time < d:
                    twist.linear.x = float(params["x"])
                    twist.angular.z = float(params["z"])
                    self.__cmd_pub.publish(twist)
                    r.sleep()
        except (TypeError, ValueError):
            pass
        
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self.__cmd_pub.publish(twist)
    
    def _on_shutdown(self):
        logmsg = "AWSIoT#_on_shutdown is_connected={}".format(self.is_connected)
        rospy.loginfo(logmsg)
        if self.is_connected:
            self.__client.loop_stop()
            self.__client.disconnect()