from machine import ADC, Pin, SoftI2C
from lyhlcd1602 import LCD
import time
import sys
import array
import struct
import select

def simpson(signal,dt):
    # integrates signal
    n = len(signal) #n must be odd!
    integral = (dt/3) * (signal[0] + 2*sum(signal[:n-2:2]) \
            + 4*sum(signal[1:n-1:2]) + signal[n-1])
    return integral

def get_power(volts,amps):
    # read ADCs and returns cycle-averaged power as float
    for i in range(ndata):
        volts[i] = adc0.read_u16()
        amps[i] = adc1.read_u16()
        time.sleep_us(delay_us)
    # calculate average power
    avvolts = sum(volts)/ndata
    avamps = sum(amps)/ndata
    volts = [(float(x) - avvolts) for x in volts]
    amps = [(float(x) - avamps) for x in amps]
    power = [x*y for x,y in zip(volts,amps)]
    return -5.208e-6*simpson(power,dt)*60/ncyc

# set up LED
led = Pin(25, Pin.OUT)

# Set up 1602 LCD deisplay
lcd = LCD(SoftI2C(scl=Pin(1), sda=Pin(0), freq=100000))
lcd.puts("Powermeter 1.0")
time.sleep_ms(4000)
lcd.puts('                ')

# Set up ADCs
adc0 = ADC(26)
adc1 = ADC(27)

spoll = select.poll()
spoll.register(sys.stdin, select.POLLIN)

# Set up parameters
ndata = 1001
ncyc = 3
dt = ncyc/60./ndata
dtmeas = 35.4 # measured base delay
fudge = -15
delay_us = int(round(ncyc*16666./ndata-dtmeas+fudge,0)) # Measure ndata points over ncyc cycles of 60 Hz
volts = array.array('i', 0 for i in range(ndata))
amps = array.array('i', 0 for i in range(ndata))
nexpav = 5
expav_pow = get_power(volts,amps)
while True:
    # Read data first to minimize delays
    power = get_power(volts,amps)
    expav_pow = power*2/(nexpav + 1) + expav_pow*(1 - 2/(nexpav +1)) 
    powerstring = '{:.1f}'.format(expav_pow)
    lcd.puts(powerstring+' W      ')    
 #   t0 = time.ticks_ms()
    if spoll.poll(10):
        led.value(1)
        instring = sys.stdin.buffer.read(2)       
        if instring == b'po':
            print(powerstring)
        elif instring == b'wa':
            for i in range(ndata):
                volts[i] = adc0.read_u16()
                amps[i] = adc1.read_u16()
                time.sleep_us(delay_us)
            for i in range(ndata):    
                bnum = struct.pack('H',volts[i])
                sys.stdout.buffer.write(bnum)
            time.sleep(0.05)
            for i in range(ndata):
                bnum = struct.pack('H',amps[i])
                sys.stdout.buffer.write(bnum) 
        led.value(0)
    time.sleep(0.1)
        