# Program by Shore to measure two temperatures HWS and HWR, plus boiler status
# on a Raspberry Pi Pico W, and write the data to the IoT cloud ThingSpeak
# and display it there.  Thanks to hippy from Raspberry Pi Forum for program help.
#     Mathworks info,, to see channel data (not much happening in summer)
#     https://thingspeak.com/channels/2016936/
#        PicoW at Boiler
#        Channel ID: 2016936
#        Author: ShoreNice
#        Access: Public

import machine
import urequests 
from machine import Pin,Timer
import network, time
import utime
import math

####
thermistor28 = machine.ADC(28)  #hwr, hot water return, 10K NTC thermistor typical
thermistor27 = machine.ADC(27)  #hws, hot water supply temperature
sensor_temp = machine.ADC(4) #internal gpio29, internal temperature of Pico W
conversion_factor = 3.3 / (65535) # for internal temperature of Pico W
boiler = Pin(14, Pin.IN, Pin.PULL_UP) #boiler status
#######


#######
led = Pin("LED", Pin.OUT)  #pico w led flasher
tim = Timer()
HTTP_HEADERS = {'Content-Type': 'application/json'} 
THINGSPEAK_WRITE_API_KEY = 'EP6U2secret1823N'  
 
ssid = 'myssid'
password = 'mypasswrd'


# Configure Pico W as Station
sta_if=network.WLAN(network.STA_IF)
sta_if.active(True)
 
for _ in range(10):
        print('connecting to network...') 
        sta_if.connect(ssid, password)
        time.sleep(1)
        if sta_if.isconnected():
            print('Connected.')
            break
        time.sleep(11)
 
print('network config:', sta_if.ifconfig()) 
def tick(timer):
    global led
    led.toggle()

tim.init(freq=1, mode=Timer.PERIODIC, callback=tick)

while True:
    print("Getting data to send")
    time.sleep(11)
    ##### HWR
    temperature28_value = thermistor28.read_u16()
    Vr28 = 3.3 * float(temperature28_value) / 65535
    Rt28 = 10600 * Vr28 / (3.3 - Vr28)
    temp28 = 1/(((math.log(Rt28 / 10000)) / 3950) + (1 / (273.15+25)))
    Cel28 = temp28 - 273.15
    Fah28 = Cel28 * 1.8 + 32 + 2.0
    #print ('Celsius: %.2f C  Fahrenheit: %.2f F' % (Cel28, Fah28))
    utime.sleep_ms(200)
    
    ##### HWS
    temperature27_value = thermistor27.read_u16()
    Vr27 = 3.3 * float(temperature27_value) / 65535
    Rt27 = 9925 * Vr27 / (3.3 - Vr27)
    temp27 = 1/(((math.log(Rt27 / 10000)) / 3950) + (1 / (273.15+25)))
    Cel27 = temp27 - 273.15
    Fah27 = Cel27 * 1.8 + 32
    #print ('Celsius: %.2f C  Fahrenheit: %.2f F' % (Cel27, Fah27))
    utime.sleep_ms(200)
    
    ##### PICO W TEMP
   
    reading = sensor_temp.read_u16() * conversion_factor
    temperature = (27 - (reading - 0.706)/0.001721)
    fahrenheit = ((temperature*(9/5))+32)
    #print(fahrenheit)
    utime.sleep(2)
   
    time.sleep(5)
    boilerstatus = 1 - boiler.value() # reverse so that relay closed = on
    
    t2 = (Fah27) #HWS
    t3 = (Fah28) #HWR
    #####
    t  = (fahrenheit) #PICO TEMP
    kw = boilerstatus * 10 * ((Fah27 - Fah28))/6.2
    costperhour = kw * .13  #in winter, more in summer...
    costpermonth = costperhour * 24 * 30
    deltaT = (Fah27 - Fah28)
    print("Temperature Pico: {}".format(fahrenheit))
    print("Temperature HWS: {}".format(Fah27))
    print("Temperature HWR: {}".format(Fah28))
    print("Boiler Status: {}".format(boilerstatus))
    readings = {'field1':t, 'field2':t2, 'field3':t3,'field4':kw, 'field5':costperhour,'field7':deltaT, 'field8':boilerstatus}
    # fields 4,5,7 are generated by Mathlab in cloud at ThingSpeak, field 6 is Spare
    # fields 4,5,7 are KW, $/hour, and deltaT (difference between HWS and HWR
    
    for retries in range(60):     # 60 second reboot timeout
        if sta_if.isconnected():
            print("Connected, sending")
            try:
                request = urequests.post( 'http://api.thingspeak.com/update?api_key=' + THINGSPEAK_WRITE_API_KEY, json = readings, headers = HTTP_HEADERS )  
                request.close()
                time.sleep(20)
                print("Write Data to ThingSpeak ",readings)
                print(" Successful  ")
                break
            except:
                print("Send failed")
                time.sleep(1) 
        else:
                print(" waiting for wifi to come back.....")
                time.sleep(1)
    else:
        print("Rebooting")
        time.sleep(1)
        machine.reset()   
print("Sent, waiting awhile")
time.sleep(10) 
