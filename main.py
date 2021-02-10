import RPi.GPIO as GPIO
import time
import I2C_LCD_driver
import requests
import json
from threading import Thread

numberList = []
prevStatus = None

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(25,GPIO.OUT) #GPIO25 as Trig
GPIO.setup(27,GPIO.IN) #GPIO27 as Echo
GPIO.setup(18,GPIO.OUT) #set GPIO 18 as output (buzzer)
GPIO.setup(26,GPIO.OUT) #set GPIO 26 as output (servo motor)
PWM=GPIO.PWM(26,50) #set 50Hz PWM output at GPIO26

LCD = I2C_LCD_driver.lcd() #instantiate an lcd object, call it LCD

# These are the GPIO pin numbers where the
# lines of the keypad matrix are connected
L1 = 6
L2 = 20
L3 = 19
L4 = 13

# These are the four columns
C1 = 12
C2 = 5
C3 = 16

# The GPIO pin of the column of the key that is currently
# being held down or -1 if no key is pressed
keypadPressed = -1


secretCode = "123"
input = ""

# Setup GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(L1, GPIO.OUT)
GPIO.setup(L2, GPIO.OUT)
GPIO.setup(L3, GPIO.OUT)
GPIO.setup(L4, GPIO.OUT)

# Use the internal pull-down resistors
GPIO.setup(C1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(C2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(C3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# This callback registers the key that was pressed
# if no other key is currently pressed
def keypadCallback(channel):
    global keypadPressed
    if keypadPressed == -1:
        keypadPressed = channel

# Detect the rising edges on the column lines of the
# keypad. This way, we can detect if the user presses
# a button when we send a pulse.
GPIO.add_event_detect(C1, GPIO.RISING, callback=keypadCallback)
GPIO.add_event_detect(C2, GPIO.RISING, callback=keypadCallback)
GPIO.add_event_detect(C3, GPIO.RISING, callback=keypadCallback)

# Sets all lines to a specific state. This is a helper
# for detecting when the user releases a button
def setAllLines(state):
    GPIO.output(L1, state)
    GPIO.output(L2, state)
    GPIO.output(L3, state)
    GPIO.output(L4, state)

def checkSpecialKeys(count):
    global input
    pressed = False

    GPIO.output(L4, GPIO.HIGH)

    if (GPIO.input(C3) == 1):
        print("Input reset!");
        pressed = True

    if (not pressed and GPIO.input(C1) == 1):
        if input == secretCode:
            print("Code correct!")
            LCD.backlight(1) #turn backlight on
            LCD.lcd_clear() #clear the display
            LCD.lcd_display_string("Welcome home!", 1) #write on line 1
        
            PWM.start(3) #open door
            time.sleep(5) #allow time for movement
            PWM.start(12) #close door
    
            LCD.lcd_clear() #clear the display
            #upload to thingspeak 
            resp=requests.get("https://api.thingspeak.com/update?api_key=Q539CRA8JC5EWP86&field1=1")
            input = ""
            start()
        else:
            print("Incorrect code!")
            LCD.backlight(1) #turn backlight on
            LCD.lcd_clear() #clear the display
            LCD.lcd_display_string("Password incorrect!", 1) #write on line 1
            LCD.lcd_display_string("Please try again...", 2) #write on line 2
            time.sleep(2) #wait 2 sec
        
            GPIO.output(18,1) #output logic high/'1'
            time.sleep(0.5)
            GPIO.output(18,0) #output logic high/'1'
            time.sleep(0.5)
            GPIO.output(18,1) #output logic high/'1'
            time.sleep(0.5)
            GPIO.output(18,0) #output logic high/'1'
            time.sleep(0.5)
            GPIO.output(18,1) #output logic high/'1'
            time.sleep(0.5)
            GPIO.output(18,0) #output logic high/'1'

            count = count + 1
            print(count)
            if count >= 3:
                LCD.backlight(1) #turn backlight on
                LCD.lcd_clear() #clear the display
                LCD.lcd_display_string("Sending tweet...", 1) #write on line 1
                time.sleep(3) #wait 2 sec
                #tweet to owner that someone has tried the password incorrectly too many times
                resp=requests.post("https://api.thingspeak.com/apps/thingtweet/1/statuses/update",
                       json={"api_key":"7ATM4DOFKZYR1OQ1","status":"Intruder alert! Someone entered the password incorrectly too many times!"})
                LCD.lcd_clear() #clear the display
                input = ""
                start()
            else:
                input = ""
                keypad(count, -1)
        pressed = True

    GPIO.output(L3, GPIO.LOW)

    if pressed:
        input = ""

    return pressed

# reads the columns and appends the value, that corresponds
# to the button, to a variable
def readLine(line, characters):
    global input
    # We have to send a pulse on each line to
    # detect button presses
    GPIO.output(line, GPIO.HIGH)
    if(GPIO.input(C1) == 1):
        input = input + characters[0]
    if(GPIO.input(C2) == 1):
        input = input + characters[1]
    if(GPIO.input(C3) == 1):
        input = input + characters[2]
    GPIO.output(line, GPIO.LOW)


#define a function called distance below:
def distance():
    #produce a 10us pulse at Trig
    GPIO.output(25,1) 
    time.sleep(0.00001)
    GPIO.output(25,0)

    #measure pulse width (i.e. time of flight) at Echo
    StartTime=time.time()
    StopTime=time.time()
    while GPIO.input(27)==0:
        StartTime=time.time() #capture start of high pulse       
    while GPIO.input(27)==1:
        StopTime=time.time() #capture end of high pulse
    ElapsedTime=StopTime-StartTime

    #compute distance in cm, from time of flight
    Distance=(ElapsedTime*34300)/2
       #distance=time*speed of ultrasound,
       #/2 because to & fro
    return Distance

def keypad(count, keypadPressed):
    def check():
        time.sleep(10)
        if input == '':
            dist = distance()
            if dist < 10:
                LCD.backlight(1) #turn backlight on
                LCD.lcd_clear() #clear the display
                LCD.lcd_display_string("Sending tweet...", 1) #write on line 1
                time.sleep(2)
                LCD.lcd_clear() #clear the display
                #tweet to the owner
                resp=requests.post("https://api.thingspeak.com/apps/thingtweet/1/statuses/update",
                       json={"api_key":"7ATM4DOFKZYR1OQ1","status":"Intruder alert! Something might be in front of your door! Check the camera feed."})

    Thread(target = check).start()

    while True:
        # If a button was previously pressed,
        # check, whether the user has released it yet
        if keypadPressed != -1:
            setAllLines(GPIO.HIGH)
            if GPIO.input(keypadPressed) == 0:
                keypadPressed = -1
            else:
                time.sleep(0.1)
        # Otherwise, just read the input
        else:
            if count < 3:
                if not checkSpecialKeys(count):
                    print(input)
                    readLine(L1, ["1","2","3"])
                    readLine(L2, ["4","5","6"])
                    readLine(L3, ["7","8","9"])
                    readLine(L4, ["*","0","#"])
                    time.sleep(0.1)
                else:
                    time.sleep(0.1)
            else:
                pass
    
def retrieveThingSpeakDoor():
    resp=requests.get("https://api.thingspeak.com/channels/1230188/fields/2.json") #to read only field 1, 1 values
    results=json.loads(resp.text) #convert json into Python object
    feeds = results["feeds"]
    for x in range(len(feeds)):
        if feeds[x]["field2"] != None:
            numberList.append(int(feeds[x]["field2"]))
    print(numberList[len(numberList)-1])
    return numberList[len(numberList)-1]

def retrieveThingSpeakBuzzer():
    resp=requests.get("https://api.thingspeak.com/channels/1230188/fields/3.json") #to read only field 1, 1 values
    results=json.loads(resp.text) #convert json into Python object
    feeds = results["feeds"]
    for x in range(len(feeds)):
        if feeds[x]["field3"] != None:
            numberList.append(int(feeds[x]["field3"]))
    print(numberList[len(numberList)-1])
    return numberList[len(numberList)-1]

def retrieveThingSpeakStatus():
    resp=requests.get("https://api.thingspeak.com/channels/1230188/status.json") #to read only field 1, 1 values
    results=json.loads(resp.text)
    feeds = results["feeds"]
    for x in range(len(feeds)):
        if feeds[x]["status"] != None:
            numberList.append(feeds[x]["status"])
    print(numberList[len(numberList)-1])
    return numberList[len(numberList)-1]

def start():
    while (True):
        print("Measured distance = {0:0.1f} cm".format(distance()))
    
        dist = distance()
        time.sleep(1)

        #status = retrieveThingSpeakStatus()
        #if prevStatus != status:
        #    prevStatus = status
        #    LCD.backlight(1) #turn backlight on
        #    LCD.lcd_clear() #clear the display
        #    LCD.lcd_display_string(status, 1) #write on line 1
        #    time.sleep(5) #wait 3 sec
        #    LCD.lcd_clear() #clear the display

        #door = retrieveThingSpeakDoor()
        #if door == 1:
        #    PWM.start(3) #open door
        #    time.sleep(2) #allow time for movement
        #if door == 0:
        #    PWM.start(12) #close door
        #    time.sleep(2) #allow time for movement

        #buzzer = retrieveThingSpeakBuzzer()
        #if buzzer == 1:
        #    GPIO.output(18,1) #output logic high/'1'
        #if buzzer == 0:
        #    GPIO.output(18,0) #output logic high/'1'
        
        if dist < 10:
            LCD.backlight(1) #turn backlight on 
            LCD.lcd_display_string("Hello there!", 1) #write on line 1
            LCD.lcd_display_string("Key in passcode", 2) #write on line 2
            keypad(0, -1)
        
        
start()
