#!/usr/bin/env python
# encoding: utf-8

"""
controlcenter.py

Created by William Woodall on 2010-04-22.
"""
__author__ = "William Woodall"
__copyright__ = "Copyright (c) 2009 William Woodall"

###  Imports  ###

# Standard Python Libraries
import sys
import os
import telnetlib
import time
from socket import *

from logerror import logError

try: # try to catch any missing dependancies
# <PKG> for <PURPOSE>
    PKGNAME = 'pygame'
    import pygame
    from pygame.locals import *
    
    PKGNAME= 'Simple PyGame GUI'
    sys.path.append('vendor')
    import gui
    from gui import *
    
    PKGNAME = 'pyserial'
    import serial
    from serial import Serial

    del PKGNAME
except ImportError as e: # We are missing something, let them know...
    sys.stderr.write("You might not have the "+PKGNAME+" module, try 'easy_install "+PKGNAME+"', else consult google.\n"+str(e)+"\n")
    sys.exit(-1)

###  Static Variables  ###
# Joystick Defaults (Don't change here change in Joystick Control)
DEAD_MAN_BUTTON = 4

SPEED_AXIS = 1
INVERT_SPEED = True
SPEED_SCALAR = 1.11

DIRECTION_AXIS = 0
INVERT_DIRECTION = True
DIRECTION_SCALAR = 1.11

SPEED_AND_DIRECTION_SENSITIVITY = .05
SPEED_AND_DIRECTION_DEAD_ZONE = .25

LIFT_AND_BUCKET_AXIS = 3
LIFT_AND_BUCKET_SCALAR = 1.33
LIFT_AND_BUCKET_TOGGLE_BUTTON = 5
IF_BUCKET = 1

INVERT_LIFT = False
LIFT_SENSITIVITY = .1
LIFT_DEAD_ZONE = .25

INVERT_BUCKET = False
BUCKET_SENSITIVITY = .1
BUCKET_DEAD_ZONE = .25

# Serial
DEFAULT_SERIAL_PORT = "COM9"

# GUI
X = 1280
Y = 800
X_BUFFER = 30
Y_BUFFER = 30

###  Classes  ###

class joystick_handler(object):
    """Joystick proxy, Taken and modified from: http://bitbucket.org/denilsonsa/pygame-joystick-test"""
    def __init__(self, joy_id):
        self.id = joy_id
        self.joy = pygame.joystick.Joystick(joy_id)
        self.name = self.joy.get_name()
        self.joy.init()
        self.numaxes    = self.joy.get_numaxes()
        self.numballs   = self.joy.get_numballs()
        self.numbuttons = self.joy.get_numbuttons()
        self.numhats    = self.joy.get_numhats()
        
        self.axis = []
        for i in xrange(self.numaxes):
            self.axis.append(self.joy.get_axis(i))
            
        self.ball = []
        for i in xrange(self.numballs):
            self.ball.append(self.joy.get_ball(i))
            
        self.button = []
        for i in xrange(self.numbuttons):
            self.button.append(self.joy.get_button(i))
            
        self.hat = []
        for i in xrange(self.numhats):
            self.hat.append(self.joy.get_hat(i))
    
    def __repr__(self):
        result = ""
        result += "Joystick %s\n" % self.name
        if self.numaxes > 0:
            result += "Axes:\n"
            for axis in xrange(self.numaxes):
                result += "Axis %d: %1.10f\n" % (axis, self.axis[axis])
            if result[-1] != "\n": result += "\n"
        if self.numballs > 0:
            result += "Balls:\n"
            for ball in xrange(self.numballs):
                result += "Ball %d: %1.10f  " % (ball, self.ball[ball])
                if ball % 2 == 1:
                    result += "\n"
            if result[-1] != "\n": result += "\n"
        if self.numbuttons > 0:
            result += "Buttons:\n"
            for button in xrange(self.numbuttons):
                result += "Button %2d: %d" % (button, self.button[button])
                if (button+1) % 6 == 0:
                    result += "\n"
                elif button != self.numbuttons-1:
                    result += " | "
            if result[-1] != "\n": result += "\n"
        if self.numhats > 0:
            result += "Hats:\n"
            for hat in xrange(self.numhats):
                result += "Hat "+str(hat)+": "+str(self.hat[hat])+"\n"
            if result[-1] != "\n": result += "\n"
        return result
    
    def quit(self):
        """uninit the joystick"""
        if self.joy.get_init():
            self.joy.quit()
    

class Excavator(object):
    """Proxy for the Arduino controlling the excavator"""
    def __init__(self, desktop, comm_port=None, comm_type="Telnet"):
        self.comm_port = comm_port
        self.comm_type = comm_type
        
        self.desktop = desktop
        
        self.debug_window = Label(position = (300,210),size = (200,100), parent = self.desktop, text = "Excavator Output:")
        
        self.speed = 0
        self.direction = 0
        self.lift = 0
        self.bucket = 0
    
    def updateDisplay(self):
        """Updates the debug display"""
        output = "Excavator Output:\n"
        output += "Speed:        "+str(self.speed)+"\n"
        output += "Direction:    "+str(self.direction)+"\n"
        output += "Left Motor:   "+str(self.left)+"\n"
        output += "Right Motor:  "+str(self.right)+"\n"
        output += "Lift Speed:   "+str(self.lift)+"\n"
        output += "Bucket Speed: "+str(self.bucket)+"\n"
        self.debug_window.text = output
    
    def move(self):
        """Sends the current speed as a command to the excavator"""
        bucket_speed = self.speed
        leftSpeed = self.speed
        rightSpeed = self.speed
        #Account for direction
        leftSpeed = leftSpeed + self.direction
        rightSpeed = rightSpeed - self.direction
        #Account for going over 1.0 or under -1.0
        if leftSpeed < -1.0:
            leftSpeed = -1.0
        if leftSpeed > 1.0:
            leftSpeed = 1.0
        if rightSpeed < -1.0:
            rightSpeed = -1.0
        if rightSpeed > 1.0:
            rightSpeed = 1.0
        #Send the commands
        leftSpeed *= 64
        rightSpeed *= 64
        
        self.left = leftSpeed
        self.right = rightSpeed
        
        try:
            if self.comm_port:
                self.comm_port.write(" m 2 "+str(int(leftSpeed))+"\r")
                self.comm_port.write(" m 1 "+str(int(rightSpeed))+"\r")
        except:
            logError(sys.exc_info(), self.desktop.logerr, "Exception when sending commands to Excavator, if the comm_port \nisn't connected maybe a powerloss on the lantrix board occured: ")
    
    def sendLift(self):
        """Sends the current lift as a command to the excavator"""
        lift_speed = self.lift
        if lift_speed < -1.0:
            lift_speed = -1.0
        if lift_speed > 1.0:
            lift_speed = 1.0
        lift_speed *= 64
        try:
            if self.comm_port:
                self.comm_port.write(" a 1 "+str(int(lift_speed))+"\r")
        except:
            logError(sys.exc_info(), self.desktop.logerr, "Exception when sending commands to Excavator, if the comm_port \nisn't connected maybe a powerloss on the lantrix board occured: ")
    
    def sendBucket(self):
        """Sends the current bucket as a command to the excavator"""
        bucket_speed = self.bucket
        if bucket_speed < -1.0:
            bucket_speed = -1.0
        if bucket_speed > 1.0:
            bucket_speed = 1.0
        bucket_speed *= 64
        try:
            if self.comm_port:
                self.comm_port.write(" a 2 "+str(int(bucket_speed))+"\r")
        except:
            logError(sys.exc_info(), self.desktop.logerr, "Exception when sending commands to Excavator, if the comm_port \nisn't connected maybe a powerloss on the lantrix board occured: ")
    
    def update(self, joystick):
        """Updates the excavator, if necessary, given a joystick_handler"""
        try:
            if not self.comm_port or not joystick:
                self.debug_window.text = "Excavator Output:\nNot Processing Currently."
                return
            speed_needs_to_be_updated = False
            direction_needs_to_be_updated = False
            lift_needs_to_be_updated = False
            bucket_needs_to_be_updated = False
            # The dead man button is pressed do speed and direction
            if joystick.button[DEAD_MAN_BUTTON] == 1:
                # Check if the speed needs to be updated
                temp_speed = joystick.axis[SPEED_AXIS]
                if INVERT_SPEED:
                    temp_speed *= -1
                if abs(temp_speed) < SPEED_AND_DIRECTION_DEAD_ZONE:
                    self.speed = 0
                    speed_needs_to_be_updated = True
                elif abs(self.speed - temp_speed) >= SPEED_AND_DIRECTION_SENSITIVITY:
                    self.speed = temp_speed*SPEED_SCALAR
                    speed_needs_to_be_updated = True
                # Check if the speed needs to be updated
                temp_direction = joystick.axis[DIRECTION_AXIS]
                if INVERT_DIRECTION:
                    temp_direction *= -1
                if abs(temp_direction) < SPEED_AND_DIRECTION_DEAD_ZONE:
                    self.direction = 0
                    direction_needs_to_be_updated = True
                elif abs(self.direction - temp_direction) >= SPEED_AND_DIRECTION_SENSITIVITY:
                    self.direction = temp_direction*DIRECTION_SCALAR
                    direction_needs_to_be_updated = True
            else: # Dead man switch off, stop the motors
                self.speed = 0
                speed_needs_to_be_updated = True
                self.direction = 0
                direction_needs_to_be_updated = True
            # Check if the lift/bucket needs to be updated
            if joystick.button[LIFT_AND_BUCKET_TOGGLE_BUTTON] == IF_BUCKET: # If the bucket
                self.lift = 0
                lift_needs_to_be_updated = True
                temp_bucket = joystick.axis[LIFT_AND_BUCKET_AXIS]
                if INVERT_BUCKET:
                    temp_bucket *= -1
                if abs(temp_bucket) < BUCKET_DEAD_ZONE:
                    self.bucket = 0
                    bucket_needs_to_be_updated = True
                elif abs(self.bucket - temp_bucket) >= BUCKET_SENSITIVITY:
                    self.bucket = temp_bucket*LIFT_AND_BUCKET_SCALAR
                    bucket_needs_to_be_updated = True
            else: # If the Lift
                self.bucket = 0
                bucket_needs_to_be_updated = True
                temp_lift = joystick.axis[LIFT_AND_BUCKET_AXIS]
                if INVERT_LIFT:
                    temp_lift *= -1
                if abs(temp_lift) < LIFT_DEAD_ZONE:
                    self.lift = 0
                    lift_needs_to_be_updated = True
                if abs(self.lift - temp_lift) >= LIFT_SENSITIVITY:
                    self.lift = temp_lift*LIFT_AND_BUCKET_SCALAR
                    lift_needs_to_be_updated = True
            # Send new commands if necessary
            if speed_needs_to_be_updated or direction_needs_to_be_updated:
                self.move()
            if lift_needs_to_be_updated:
                self.sendLift()
            if bucket_needs_to_be_updated:
                self.sendBucket()
            # Update the display
            self.updateDisplay()
        except:
            logError(sys.exc_info(), self.desktop.logerr, "Exception reading joystick data @ %s: " % str(time.time()))
    

class TestingCommPort(object):
    """Stub comm port for testing, logs out going data to a file"""
    def __init__(self):
        self.log_file = open("testing_output.txt", "w+")
    
    def read(self, bytes = 0):
        """Reads"""
        pass
    
    def write(self, message):
        """Writes the message to a logging file"""
        self.log_file.write(message)

class ControlCenterDesktop(Desktop):
    """The main control center window"""
    def __init__(self):
        Desktop.__init__(self)
        self.running = True
        self.comm_mode = "Telnet"
        
        self.layoutDesktop()
        
        # Setup exit button
        exit_button_image = pygame.image.load('vendor/art/exit.png').convert()
        exit_button_style = createImageButtonStyle(exit_button_image, 15)
        self.exit_button = ImageButton((X-20,10), self, exit_button_style)
        self.exit_button.onClick = self.close
        
        # Initialize the Error display
        self.error_display = ErrorDisplay(self)
        self.logerr = self.error_display.logerr
        
        # Initialize the FPS Display
        self.fps_display = FPSDisplay(self)
        self.fps_label = self.fps_display.fps_label
        
        # Initialize telnet_serial_selector
        self.telnet_serial_selector = TelnetSerialSelector(self)
        
        # Setup the Serial Controls
        self.serial_controls = SerialControls(self)
        self.serial_controls.hide()
        
        # Setup the Telnet Controls
        self.telnet_controls = TelnetControls(self)
        
        # Setup the Testing Controls
        self.testing_controls = TestingControls(self)
        
        # Setup Joystick Control
        self.joystick_controls = JoystickControl(self)
        self.joy = self.joystick_controls.joystick
        
        # Setup Excavator Proxy
        self.excavator = Excavator(self)
    
    def close(self, button=None):
        """Called when the program needs to exit"""
        if self.comm_mode == "Telnet":
            self.telnet_controls.disconnect(None)
        elif self.comm_mode == "Serial":
            self.serial_controls.disconnect(None)
        else:
            self.testing_controls.disconnect(None)
        self.running = False
    
    def switchToTelnet(self):
        """Performs necessary actions to switch to telnet communication mode"""
        self.comm_mode = "Telnet"
        self.serial_controls.hide()
        self.telnet_controls.show()
        self.testing_controls.hide()
    
    def switchToSerial(self):
        """Performs necessary actions to switch to serial communication mode"""
        self.comm_mode = "Serial"
        self.telnet_controls.hide()
        self.serial_controls.show()
        self.testing_controls.hide()
        
    def switchToTesting(self):
        """Performs necessary actions to switch to Testing Mode"""
        self.comm_mode = "Serial"
        self.telnet_controls.hide()
        self.serial_controls.hide()
        self.testing_controls.show()
    
    def connected(self):
        """Called when we are connected to the Excavator"""
        if self.comm_mode == "Telnet":
            self.excavator.comm_mode = "Telnet"
            self.excavator.comm_port = self.telnet_controls.telnet
            self.telnet_controls.remote_start_button.enabled = True
        elif self.comm_mode == "Serial":
            self.excavator.comm_mode = "Serial"
            self.excavator.comm_port = self.serial_controls.serial
        elif self.comm_mode == "Testing":
            self.excavator.comm_mode = "Testing"
            self.excavator.comm_port = TestingCommPort()
        self.joystick_controls.enable()
    
    def disconnected(self):
        """Called when we are disconnected from the Excavator"""
        if self.comm_mode == "Telnet":
            self.telnet_controls.sendRemoteStop()
            self.telnet_controls.remote_start_button.enabled = False
        self.joystick_controls.disable()
    
    def layoutDesktop(self):
        """Initial setup for the desktop"""
        # Setup background image
        self.bg_image = pygame.image.load('vendor/art/back.png').convert()
        # Set the Title bar text
        display.set_caption('Auburn Lunar Excavator Control Center')
    
    def update(self):
        """Overrides the builtin update"""
        self.joystick_controls.update()
        Desktop.update(self)
    

class TelnetControls(object):
    """Contains elements related to connecting and controlling via telnet"""
    def __init__(self, desktop):
        self.desktop = desktop
        
        y_offset = 55
        
        self.telnet = None
        
        # Connect button
        self.connect_button = Button(position = (X_BUFFER, y_offset), size = (100,0), parent = desktop, text = "Connect")
        self.connect_button.onClick = self.connect
        
        # Telnet IP text box
        self.telnet_ip = TextBox(position = (X_BUFFER+110, y_offset), size = (200, 0), parent = desktop, text = "192.168.1.5:5000")
        
        # Remote Start button
        self.remote_start_button = Button(position = (X_BUFFER, y_offset+25), size = (100,0), parent = desktop, text = "Remote Start")
        self.remote_start_button.onClick = self.sendRemoteStart
        self.remote_start_button.enabled = False
    
    def sendRemoteStart(self, button=None):
        """Sends the remote start command to the excavator"""
        # Send magic packet
        try:
            udp_socket = socket(AF_INET, SOCK_DGRAM)
            msg = '\x1B'+'\x01\x00\x00\x00'+'\x01\x00\x00\x00'
            host, _ = self.telnet_ip.text.split(':')
            udp_socket.sendto(msg, (host,0x77f0))
            udp_socket.close()
        except:
            logError(sys.exc_info(), self.desktop.logerr, "Exception Sending Start Command: ")
        # Reconfigure button
        self.remote_start_button.text = "Remote Stop"
        self.remote_start_button.onClick = self.sendRemoteStop
    
    def sendRemoteStop(self, button=None):
        """Sends the remote stop command to the excavator"""
        # Send magic packet
        try:
            udp_socket = socket(AF_INET, SOCK_DGRAM)
            msg = '\x1B'+'\x01\x00\x00\x00'+'\x00\x00\x00\x00'
            host, _ = self.telnet_ip.text.split(':')
            udp_socket.sendto(msg, (host,0x77f0))
            udp_socket.close()
        except:
            logError(sys.exc_info(), self.desktop.logerr, "Exception Sending Stop Command: ")
        # Reconfigure button
        self.remote_start_button.text = "Remote Start"
        self.remote_start_button.onClick = self.sendRemoteStart
    
    def connect(self, button):
        """Called when connect is clicked"""
        # Try to connect
        try:
            host, port = self.telnet_ip.text.split(":")
            self.telnet = telnetlib.Telnet(host, int(port), 30)
        except:
            logError(sys.exc_info(), self.desktop.logerr, "Exception connecting via Telnet, %s:%s: " % (type(host), type(port)))
        # Disable the connector
        self.desktop.telnet_serial_selector.disable()
        # Change the connect button to disconnect
        self.connect_button.text = "Disconnect"
        self.connect_button.onClick = self.disconnect
        # Nofity the desktop
        self.desktop.connected()
    
    def disconnect(self, button):
        """Called when disconnect clicked"""
        self.sendRemoteStop()
        # Disconnect from telnet
        if self.telnet:
            self.telnet.close()
        self.telnet = None
        # Enable the connectors
        self.desktop.telnet_serial_selector.enable()
        # Change the disconnect button to connect
        self.connect_button.text = "Connect"
        self.connect_button.onClick = self.connect
        # Nofity the desktop
        self.desktop.disconnected()
    
    def hide(self):
        """Hides all the elements"""
        self.connect_button.visible = False
        self.telnet_ip.visible = False
        self.remote_start_button.visible = False
    
    def show(self):
        """Shows all the elements"""
        self.connect_button.visible = True
        self.telnet_ip.visible = True
        self.remote_start_button.visible = True
    

class TestingControls(object):
    """Contains elements related to connecting and controlling using test mode"""
    def __init__(self, desktop):
        self.desktop = desktop
        
        y_offset = 55
        
        # Connect button
        self.connect_button = Button(position = (X_BUFFER, y_offset), size = (100,0), parent = desktop, text = "Connect")
        self.connect_button.onClick = self.connect
    
    def connect(self, button):
        """Called when connect is clicked"""
        # Disable the connector
        self.desktop.telnet_serial_selector.disable()
        # Change the connect button to disconnect
        self.connect_button.text = "Disconnect"
        self.connect_button.onClick = self.disconnect
        # Nofity the desktop
        self.desktop.connected()
    
    def disconnect(self, button):
        """Called when disconnect clicked"""
        # Enable the connectors
        self.desktop.telnet_serial_selector.enable()
        # Change the disconnect button to connect
        self.connect_button.text = "Connect"
        self.connect_button.onClick = self.connect
        # Nofity the desktop
        self.desktop.disconnected()
    
    def hide(self):
        """Hides all the elements"""
        self.connect_button.visible = False
    
    def show(self):
        """Shows all the elements"""
        self.connect_button.visible = True
    

class SerialControls(object):
    """Contains elements related to connecting and controlling via serial"""
    def __init__(self, desktop):
        self.desktop = desktop
        self.serial = None
        
        y_offset = 55
        
        # Connect button
        self.connect_button = Button(position = (X_BUFFER, y_offset), size = (100,0), parent = desktop, text = "Connect")
        self.connect_button.onClick = self.connect
        
        # Serial Port text box
        self.serial_txt = TextBox(position = (X_BUFFER+110, y_offset), size = (200, 0), parent = desktop, text = DEFAULT_SERIAL_PORT)
    
    def connect(self, button):
        """Called when connect is clicked"""
        try:
            # Try to connect
            self.serial = Serial()
            self.serial.port = self.serial_txt.text
            self.serial.baudrate = 19200
            self.serial.open()
            # Disable the connector
            self.desktop.telnet_serial_selector.disable()
            # Change the connect button to disconnect
            self.connect_button.text = "Disconnect"
            self.connect_button.onClick = self.disconnect
            # Nofity the desktop
            self.desktop.connected()
        except Exception as err:
            logError(sys.exc_info(), self.desktop.logerr, "Exception opening the serial port:")
    
    def disconnect(self, button):
        """Called when disconnect clicked"""
        # Disconnect from serial
        if self.serial and self.serial.isOpen():
            self.serial.close()
        self.serial = None
        # Enable the connectors
        self.desktop.telnet_serial_selector.enable()
        # Change the disconnect button to connect
        self.connect_button.text = "Connect"
        self.connect_button.onClick = self.connect
        # Nofity the desktop
        self.desktop.disconnected()
    
    def hide(self):
        """Hides all the elements"""
        self.connect_button.visible = False
        self.serial_txt.visible = False
    
    def show(self):
        """Shows all the elements"""
        self.connect_button.visible = True
        self.serial_txt.visible = True
    

class TelnetSerialSelector(object):
    """Contains elements related to the Telnet or Serial radio buttons"""
    def __init__(self, desktop):
        self.desktop = desktop
        # Draw Options
        self.telnet_option = OptionBox(position = (X_BUFFER, Y_BUFFER), parent = self.desktop, text = "Telnet", value = True)
        self.telnet_option.onValueChanged = self.onValueChanged
        self.serial_option = OptionBox(position = (X_BUFFER+60, Y_BUFFER), parent = self.desktop, text = "Serial (XBee)")
        self.serial_option.onValueChanged = self.onValueChanged
        self.serial_option = OptionBox(position = (X_BUFFER+160, Y_BUFFER), parent = self.desktop, text = "No Remote (Testing)")
        self.serial_option.onValueChanged = self.onValueChanged
        
    def onValueChanged(self, widget):
        """Called when either of the options are clicked"""
        if widget.text == "Telnet" and self.desktop.comm_mode != "Telnet":
            self.desktop.comm_mode = "Telnet"
            self.desktop.switchToTelnet()
        elif widget.text == "Serial (XBee)" and self.desktop.comm_mode != "Serial":
            self.desktop.comm_mode = "Serial"
            self.desktop.switchToSerial()
        elif widget.text == "No Remote (Testing)" and self.desktop.comm_mode != "Testing":
            self.desktop.comm_mode = "Testing"
            self.desktop.switchToTesting()
            
    def disable(self):
        """Disables the options"""
        self.telnet_option.enabled = False
        self.serial_option.enabled = False
    
    def enable(self):
        """Enables the options"""
        self.telnet_option.enabled = True
        self.serial_option.enabled = True
    

class FPSDisplay(object):
    """Contatins elements related to the FPS display"""
    def __init__(self, desktop):
        self.desktop = desktop
        #Create a label passing some parameters.
        #TRICKY THING HERE: if you want to use an already defined style, just copy it, and set new parameters as you wish
        self.fpsStyle = gui.defaultLabelStyle.copy()
        self.fpsStyle['border-width'] = 0
        self.fpsStyle['wordwrap'] = True
        self.fpsStyle['autosize'] = False
        
        # FPS Label
        self.fps_label = Label(position = (X-30,Y-30),size = (30,15), parent = self.desktop, text = "00", style = self.fpsStyle)
    

class JoystickControl(object):
    """Contains all elements related to Joystick control and interaction"""
    def __init__(self, desktop):
        self.desktop = desktop
        self.joystick_names = ['Select a Joystick:']
        self.joy_list = None
        self.joystick = None
        
        self.controller_setup = "VT Controller"
        
        self.initJoystick()
        self.drawJoyList()
    
    def update(self):
        """Updates the joystick data"""
        if self.joystick:
            self.debug_label.text = repr(self.joystick)
        else:
            self.debug_label.text = "No Joystick Data"
    
    def drawJoyList(self):
        """Draws the UI elements for the Joystick control"""
        y_offset = 105
        self.joy_list = ListBox(position = (X_BUFFER, y_offset), size = (200, 100), parent = self.desktop,  items = [i for i in self.joystick_names])
        self.joy_list.onItemSelected = self.joystickSelected
        
        self.start_rc_button = Button(position = (X_BUFFER+210, y_offset), size = (100,0), parent = self.desktop, text = "Start R/C")
        self.start_rc_button.onClick = self.startRC
        
        self.vt_controller_selector = OptionBox(position = (X_BUFFER+210, y_offset+30), parent = self.desktop, text = "VT Controller", value = True)
        self.vt_controller_selector.onValueChanged = self.onSetupSelected
        self.vt_controller_selector.enabled = False
        self.xbox_controller_selector = OptionBox(position = (X_BUFFER+210, y_offset+50), parent = self.desktop, text = "XBox 360 Controller")
        self.xbox_controller_selector.onValueChanged = self.onSetupSelected
        self.xbox_controller_selector.enabled = False
        
        self.setupDebugger()
        
        self.onSetupSelected(self.xbox_controller_selector)
        
        self.disable()
    
    def onSetupSelected(self, widget):
        """Called when a controller setup is selected"""
        if widget.text == "VT Controller" and self.controller_setup != "VT Controller":
            self.controller_setup = "VT Controller"
            DEAD_MAN_BUTTON = 30
            
            SPEED_AXIS = 1
            INVERT_SPEED = True
            SPEED_SCALAR = 1.11
            
            DIRECTION_AXIS = 0
            INVERT_DIRECTION = True
            DIRECTION_SCALAR = 1.11
            
            SPEED_AND_DIRECTION_SENSITIVITY = .05
            SPEED_AND_DIRECTION_DEAD_ZONE = .25
            
            LIFT_AND_BUCKET_AXIS = 3
            LIFT_AND_BUCKET_SCALAR = 1.33
            LIFT_AND_BUCKET_TOGGLE_BUTTON = 1
            IF_BUCKET = 1
            
            INVERT_LIFT = False
            LIFT_SENSITIVITY = .1
            LIFT_DEAD_ZONE = .25
            
            INVERT_BUCKET = False
            BUCKET_SENSITIVITY = .1
            BUCKET_DEAD_ZONE = .25
        elif widget.text == "XBox 360 Controller" and self.controller_setup != "XBox 360 Controller":
            self.controller_setup = "XBox 360 Controller"
            DEAD_MAN_BUTTON = 4
            
            SPEED_AXIS = 1
            INVERT_SPEED = True
            SPEED_SCALAR = 1.11
            
            DIRECTION_AXIS = 0
            INVERT_DIRECTION = True
            DIRECTION_SCALAR = 1.11
            
            SPEED_AND_DIRECTION_SENSITIVITY = .05
            SPEED_AND_DIRECTION_DEAD_ZONE = .25
            
            LIFT_AND_BUCKET_AXIS = 3
            LIFT_AND_BUCKET_SCALAR = 1.33
            LIFT_AND_BUCKET_TOGGLE_BUTTON = 5
            IF_BUCKET = 1
            
            INVERT_LIFT = False
            LIFT_SENSITIVITY = .1
            LIFT_DEAD_ZONE = .25
            
            INVERT_BUCKET = False
            BUCKET_SENSITIVITY = .1
            BUCKET_DEAD_ZONE = .25
    
    def enable(self):
        """Enables joystick controls"""
        self.joy_list.enabled = True
        if self.joystick:
            self.start_rc_button.enabled = True
    
    def disable(self):
        """Disables joystick controls"""
        self.stopRC()
        self.joy_list.enabled = False
        self.start_rc_button.enabled = False
    
    def startRC(self, button=None):
        """Start remote control"""
        self.rc = True
        self.joy_list.enabled = False
        if self.joystick:
            self.start_rc_button.text = "Stop R/C"
            self.start_rc_button.onClick = self.stopRC
    
    def stopRC(self, button=None):
        """Stop remote control"""
        self.rc = False
        self.joy_list.enabled = True
        if self.joystick:
            del self.joystick
            self.joystick = None
        self.start_rc_button.text = "Start R/C"
        self.start_rc_button.onClick = self.startRC
    
    def joystickSelected(self, widget):
        """Called when a joystick is selected"""
        if widget.selectedIndex > 0 and widget.selectedIndex < pygame.joystick.get_count()+1:
            self.desktop.joy = self.joystick = joystick_handler(widget.selectedIndex-1)
            self.start_rc_button.enabled = True
            self.vt_controller_selector.enabled = True
            self.xbox_controller_selector.enabled = True
            if self.controller_setup == "VT Controller":
                self.vt_controller_selector.value = True
            else:
                self.xbox_controller_selector.value = True
        else:
            self.joystick = None
            self.start_rc_button.enabled = False
            self.vt_controller_selector.enabled = False
            self.xbox_controller_selector.enabled = True
    
    def setupDebugger(self):
        """Displays all the information about the joystick"""
        self.debug_label = Label(position = (30,210),size = (200,100), parent = self.desktop, text = "No Joystick Data")
    
    def initJoystick(self, button=None):
        """Initializes Joysticks"""
        pygame.joystick.init()
        # Call for joysticks to be enumerated and updated
        self.updateJoysticks()
    
    def updateJoysticks(self, button=None):
        """Updates the list of attached joysticks"""
        self.joystick_names = ['Select a Joystick:']
        # Enumerate joysticks
        for i in range(0, pygame.joystick.get_count()):
            self.joystick_names.append(pygame.joystick.Joystick(i).get_name())
    

class ErrorDisplay(Label):
    """docstring for ErrorDisplay"""
    def __init__(self, desktop):
        self.desktop = desktop
        
        errorStyle = gui.defaultLabelStyle.copy()
        errorStyle['border-width'] = 1
        errorStyle['border-color'] = (255,0,0)
        errorStyle['wordwrap'] = True
        errorStyle['autosize'] = False
        
        # Setup Log file
        self.log_file = None
        try:
            self.log_file = open("err.log", "w+")
        except Exception as err:
            logError(sys.exc_info(), self.logerr, "Exception opening log file: ")
        
        # Text box for displaying errors
        Label.__init__(self, position = (30,Y-(Y/3)-30),size = (X/2,Y/3), parent = self.desktop, text = "Error Text goes here", style = errorStyle)
        self.visible = False
        self.onClick = self.hide
    
    def logerr(self, msg):
        """Puts the error in the error box and logs it to a file"""
        # Log to a file
        if self.log_file:
            self.log_file.write(msg)
        # Put in error box
        self.text = msg
        self.visible = True
    
    def hide(self):
        """docstring for hide"""
        self.visible = False
    

###  Functions  ###

def initStyle():
    """Initializes the styles"""
    import defaultStyle
    os.chdir('vendor')
    defaultStyle.init(gui)
    os.chdir('..')

def log(msg):
    """docstring for logerr"""
    print msg

def main():
    pygame.init()
    screen = pygame.display.set_mode((X,Y), RESIZABLE)
    fullscreen = False
    clock = pygame.time.Clock()
    initStyle()
    desktop = ControlCenterDesktop()
    try:
        while desktop.running:
            clock.tick()
            # Update FPS display
            desktop.fps_label.text = str(int(clock.get_fps()))
            # Handle Events
            events = [pygame.event.wait(),]+pygame.event.get()
            for event in events:
                if event.type == QUIT:
                    desktop.running = False
                elif event.type == KEYDOWN and event.key == K_ESCAPE:
                    desktop.running = False
                elif event.type == KEYDOWN and event.key == K_f:
                    if not fullscreen:
                        screen = pygame.display.set_mode((X,Y), FULLSCREEN)
                        fullscreen = True
                    else:
                        screen = pygame.display.set_mode((X,Y), RESIZABLE)
                        fullscreen = False
                elif event.type == VIDEORESIZE:
                    screen = pygame.display.set_mode(event.size, RESIZABLE)
                elif desktop.joy == None:
                    continue
                elif event.type == JOYAXISMOTION:
                    desktop.joy.axis[event.axis] = event.value
                elif event.type == JOYBALLMOTION:
                    desktop.joy.ball[event.ball] = event.rel
                elif event.type == JOYHATMOTION:
                    desktop.joy.hat[event.hat] = event.value
                elif event.type == JOYBUTTONUP:
                    desktop.joy.button[event.button] = 0
                elif event.type == JOYBUTTONDOWN:
                    desktop.joy.button[event.button] = 1
            # End For loop
            # Update the excavator
            desktop.excavator.update(desktop.joy)
            # try:
            #     desktop.logerr(desktop.excavator.comm_port.read_some())
            # except:
            #     pass
            # Pass along the events
            gui.setEvents(events)
            # Update the Desktop
            desktop.update()
            # Begin Rendering
            screen.fill((20,40,50))
            screen.blit(desktop.bg_image, (0,0))
            desktop.draw()
            pygame.display.flip()
    except:
        logError(sys.exc_info(), log, "Exception in main Loop: ")
    finally:
        desktop.close()
    # After exiting the while loop quit
    pygame.quit()

###  IfMain  ###

if __name__ == '__main__':
    main()

