'''
MicroPython code for determining base delay in Raspberry Pi Pico when reading ADCs.
Part of project https://github.com/jabezmcc/Pico_energymeter.
Use this code on the Pico in conjunction with Read_pico_find_dt.py on the host.
Version 0.1
Jabez McCleland, July 2025
'''
from machine import ADC, Pin, SoftI2C
from lyhlcd1602 import LCD
import time
import sys
import array
import struct
import select

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
ndata = 801
delay_us = 0
volts = array.array('i', 0 for i in range(ndata))
amps = array.array('i', 0 for i in range(ndata))
while True:
    if spoll.poll(10):
        led.value(1)
        instring = sys.stdin.buffer.read(2)       
        if instring == b'po':
            pass
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
        
