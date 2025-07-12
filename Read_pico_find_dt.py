import sys
import serial
import time
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt
ndata = 801
x = np.arange(ndata)



def func(x,A,dt,phi):
    return A*np.sin(2*np.pi*60.*dt*x + phi)

port = "/dev/ttyACM0"
baudrate = 115200
serial_connection = serial.Serial(port, baudrate)
serial_connection.write(b'wa')
volts = np.empty(ndata)
amps = np.empty(ndata)
for i in range(ndata):
    result = serial_connection.read(2)
    volts[i] = int.from_bytes(result,sys.byteorder)
time.sleep(0.05)            
for i  in range(ndata):
    result = serial_connection.read(2)
    amps[i] = int.from_bytes(result,sys.byteorder)
volts = [163.45*(float(x) - sum(volts)/ndata)*3.3/65536. for x in volts]
amps = [-12.562*(float(x) - sum(amps)/ndata)*3.3/65536. for x in amps]

data = volts
popt,pcov = curve_fit(func,x,data,p0=[163,5e-5,0],method='lm')
dt_base = popt[1]
print('Measured dt is {:5.2f} us'.format(1e6*dt_base))
ncyc = 3
dt_desired = ncyc/ndata/60. 
print('ncyc =',ncyc,'npts =',ndata)
print('desired dt is {:5.2f} us.'.format(1e6*dt_desired))
if dt_base < dt_desired:
    print('Safe choice, base dt is less than desired dt.')
    print('Set the extra delay to {:3.0f} us.'.format(1e6*(dt_desired-dt_base)))
else:
    print('base_dt is greater than desired dt.  Please adjust ndata and/or ncyc')         

plt.plot(x,data)
plt.plot(x,func(x,*popt))
plt.show()

