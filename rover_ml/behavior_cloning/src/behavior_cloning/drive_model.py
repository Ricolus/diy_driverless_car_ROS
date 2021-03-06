#!/usr/bin/env python
# -*- coding: utf-8 -*-
#https://github.com/juano2310/CarND-Behavioral-Cloning-P3-Juan/blob/master/drive.py
import rospy
import time
import sys
import base64
from datetime import datetime
import os
import shutil
import numpy as np
import cv2

from geometry_msgs.msg import Twist, TwistStamped
from sensor_msgs.msg import Image,  CompressedImage
from cv_bridge import CvBridge, CvBridgeError

import json
from keras.models import model_from_json, load_model
import h5py
from keras import __version__ as keras_version

class cmd_vel_node(object):
    def __init__(self):
            
      """ROS Subscriptions """
      self.image_sub = rospy.Subscriber("/openmv_cam/image/raw",Image,self.cvt_image)
      self.image_sub = rospy.Subscriber("/raspicam_node/image/raw",Image,self.cvt_image) 
      self.image_pub = rospy.Publisher("/image_converter/output_video",Image, queue_size=10)
      self.cmdVel_pub = rospy.Publisher("/platform_control/cmd_vel", Twist, queue_size=10)
      self.cmdVelStamped_pub = rospy.Publisher('/platform_control/cmd_vel_stamped', TwistStamped, queue_size=10)

      """ Variables """
      self.model_path = 'home/wil/catkin_ws/src/diy_driverless_car_ROS/rover_ml/behavior_cloning/src/behavior_cloning/model_ack.h5'
      self.cmdvel = Twist()
      self.baseVelocity = TwistStamped()
      self.bridge = CvBridge()
      self.latestImage = None
      self.outputImage = None
      self.resized_image = None
      self.imgRcvd = False


    def cvt_image(self,data):  
      try:
        self.latestImage = self.bridge.imgmsg_to_cv2(data, "bgr8")	
      except CvBridgeError as e:
        print(e)
      if self.imgRcvd != True:
          self.imgRcvd = True    
        
    def publish(self, image,  bridge,  publisher):
        try:
            #Determine Encoding
            if np.size(image.shape) == 3: 
                imgmsg = bridge.cv2_to_imgmsg(image, "bgr8") 
            else:
                imgmsg = bridge.cv2_to_imgmsg(image, "mono8") 
            publisher.publish(imgmsg)  
        except CvBridgeError as e:
            print(e)
            
    def cmdVel_publish(self, cmdVelocity):
        
         # Publish Twist
         self.cmdVel_pub.publish(cmdVelocity)

         # Publish TwistStamped 
         self.baseVelocity.twist = cmdVelocity
         
         baseVelocity = TwistStamped()

         baseVelocity.twist = cmdVelocity
     
         now = rospy.get_rostime()
         baseVelocity.header.stamp.secs = now.secs
         baseVelocity.header.stamp.nsecs = now.nsecs
         self.cmdVelStamped_pub.publish(baseVelocity)
            
    
    def run(self):
        
         # check that model Keras version is same as local Keras version
         f = h5py.File('/home/wil/catkin_ws/src/diy_driverless_car_ROS/rover_ml/behavior_cloning/src/behavior_cloning/model.h5', mode='r')
         model_version = f.attrs.get('keras_version')
         keras_version_installed = None
         keras_version_installed = str(keras_version).encode('utf8')

         if model_version != keras_version_installed:
             print('You are using Keras version ', keras_version_installed, ', but the model was built using ', model_version)

         # Model reconstruction from JSON file

         with open('/home/wil/catkin_ws/src/diy_driverless_car_ROS/rover_ml/behavior_cloning/src/behavior_cloning/model.json', 'r') as f:
             model = model_from_json(f.read())

         model = load_model('/home/wil/catkin_ws/src/diy_driverless_car_ROS/rover_ml/behavior_cloning/src/behavior_cloning/model.h5.bak')
         
         # Load weights into the new model
         print("Model loaded.")
     
         while True:
             # Only run loop if we have an image
             if self.imgRcvd:
                 
                 # step 1: 
                 self.resized_image = cv2.resize(self.latestImage, (320,180)) 
                 
                 # step 2: 
                 image_array = np.asarray(self.resized_image)
                 
                 # step 3: 
                 
                 self.cmdvel.linear.x = 0.06
                 self.cmdvel.angular.z = float(model.predict(image_array[None, :, :, :], batch_size=1))
                 
                 #print(self.cmdvel.angular.z)
                 
                 self.cmdVel_publish(self.cmdvel)
                 
                 # Publish Processed Image
                 self.outputImage = self.latestImage
                 self.publish(self.outputImage, self.bridge,  self.image_pub)


    
def main(args):

  rospy.init_node('model_control_node', anonymous=True)

  cmd = cmd_vel_node() 

  cmd.run() 

  try:
    rospy.spin()
  except KeyboardInterrupt:
    print("Shutting down")
  cv2.destroyAllWindows()
  
if __name__ == '__main__':
    main(sys.argv)
    
