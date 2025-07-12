'''
Calibration code for Raspberry Pi Pico energy meter 
Jabez McClelland  
7/5/2025 - Version 0.0.1 - first commit

'''
import sys
import time
import numpy as np
import subprocess
import platform
import serial

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.uic import loadUiType

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

Ui_MainWindow, QMainWindow = loadUiType('calibration.ui') 
Ui_WaveformWindow, QWaveformWindow = loadUiType('waveform.ui')
Ui_AboutWindow, QAboutWindow = loadUiType('AboutEnergymeterCalib.ui')
vers = '0.0.1' 

port = "/dev/ttyACM0"
baudrate = 115200
ndata = 801
ncyc = 3
#voltfact = 163.45
#curfact = 12.562


class About(QAboutWindow, Ui_AboutWindow):
    def __init__(self):
        super(About,self).__init__()
        self.setupUi(self)
        self.versionLabel.setText("Version "+vers)
        self.licenseButt.clicked.connect(self.show_license)
        self.OKButt.clicked.connect(self.closeout)
        self.show()

    def show_license(self):
        p = platform.system()
        try:
            if p == 'Linux':
                subprocess.run(['xdg-open', 'LICENSE.txt'],check=True)
            elif p=='Windows':
                os.system('start LICENSE.txt')
            else:
                os.system('open LICENSE.txt')
        except:
             QMessageBox.warning(self,'Error','Unable to open license document')

    def closeout(self):
        self.close()
        
class ShowWaveform(QWaveformWindow,Ui_WaveformWindow):
    def __init__(self,wavedata):
        super(ShowWaveform,self).__init__()
        self.setupUi(self)
        Vcolor = 'blue'
        Acolor = 'green'
        self.buttonBox.accepted.connect(self.exit)
        self.canvas = FigureCanvas(plt.Figure())
        self.plotframeLayout.addWidget(self.canvas)
        t = wavedata[0]
        v = wavedata[1]
        vpred = wavedata[2]
        cur = wavedata[3]
        curpred = wavedata[4]
        self.ax = self.canvas.figure.subplots()
        self.ax2 = self.ax.twinx()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Raw Voltage",color=Vcolor)
        self.ax.tick_params(axis='y', colors=Vcolor)
        self.ax.axhline(y=0,color='black')
        self.ax2.set_ylabel("Raw Current",color=Acolor)       
        self.ax.set_title("Waveforms")
        self.ax.set_position([.12,.12,.75,.78])
        self.ax.tick_params(axis='both',direction='in')
        self.ax2.tick_params(axis='y',direction='in')
        self.ax.set_xlim(t[0],t[-1])        
        self.ax.plot(t,v,color=Vcolor)
        self.ax.plot(t,vpred,color='cyan')
        self.ax2.plot(t,cur,color=Acolor)
        self.ax2.plot(t,curpred,color='lightgreen')
        self.ax2.tick_params(axis='y', colors=Acolor)
        self.canvas.draw()
        self.canvas.flush_events()
        self.show()

    def exit(self):
        self.destroy()  

class Main(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(Main,self).__init__()
        self.setupUi(self)
        self.actionExitButton.triggered.connect(self.exit)
        self.menubar.setStyleSheet("QMenu::item::selected {color: rgb(30,30,30);}")
        self.actionAbout.triggered.connect(self.openabout)
        self.measvolts.setText('120.2')
        self.meascurr.setText('0.853')
        self.update_RMSpow()
        self.measvolts.returnPressed.connect(self.update_RMSpow)
        self.meascurr.returnPressed.connect(self.update_RMSpow)
        self.measurePower.clicked.connect(self.measpower)
        self.measureWaveform.clicked.connect(self.measwaveform)
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
        except:
            QMessageBox.warning(self,'Energy meter','No measurement module detected!')

    def openabout(self):
        self.aboutwin = About()
    
    def update_RMSpow(self):
        rmsvolts = float(self.measvolts.text())
        rmscurr = float(self.meascurr.text())
        self.rmspow = rmsvolts*rmscurr
        self.RMSpower_label.setText('RMS power is {:4.1f} W'.format(self.rmspow))
        
    def measpower(self):
        avpower = 0
        labelstring ='measuring'
        self.avpower_label.setText(labelstring)
        nav = 20
        for i in range(nav):
            self.ser.write(b'po')
            time.sleep(0.5)
            avpower += float(self.ser.readline().decode('utf-8').strip())
            time.sleep(0.5)
            labelstring += '.'
            self.avpower_label.setText(labelstring)
            QApplication.processEvents()
        avpower = avpower/nav
        self.avpower_label.setText('Measured RMS power is {:4.1f} W'.format(avpower))
        self.Powfact_adjust_label.setText('Please adjust powfact in pico code by a factor of {:5.4f}.'.format(self.rmspow/avpower))

    def measwaveform(self):   
        self.ser.write(b'wa')
        volts = np.empty(ndata)
        amps = np.empty(ndata)
        dt = ncyc/60./ndata
        for i in range(ndata):
            result = self.ser.read(2)
            volts[i] = int.from_bytes(result,sys.byteorder)
        time.sleep(0.05)            
        for i  in range(ndata):
            result = self.ser.read(2)
            amps[i] = int.from_bytes(result,sys.byteorder)
        volts = [(float(x) - sum(volts)/ndata)*3.3/65536. for x in volts]
        amps = [-(float(x) - sum(amps)/ndata)*3.3/65536. for x in amps]
        x = np.arange(ndata)
        v_popt,v_pcov = curve_fit(func,x,volts,p0=[1,0],method='lm')
        a_popt,a_pcov = curve_fit(func,x,amps,p0=[1,0],method='lm')
        v_pred = func(x,v_popt[0],v_popt[1])
        a_pred = func(x,a_popt[0],a_popt[1])
        wavedata = [dt*x,volts,v_pred,amps,a_pred]
        self.wfwindow = ShowWaveform(wavedata)
        vfact = abs(np.sqrt(2)*float(self.measvolts.text())/v_popt[0])
        afact = abs(np.sqrt(2)*float(self.meascurr.text())/a_popt[0])
        self.voltfact_curfact_label.setText('Please set voltfact to {:5.2f} and curfact to {:5.3f} in energymeter.py'.format(vfact,afact)) 
        
    def exit(self):
        sys.exit()

def simpson(signal,dt):
    n = len(signal) #n must be odd!
    integral = (dt/3) * (signal[0] + 2*np.sum(signal[:n-2:2]) \
            + 4*np.sum(signal[1:n-1:2]) + signal[n-1])
    return integral

def func(x,A,phi):
    return A*np.sin(2*np.pi*ncyc*x/ndata + phi)


def rotate(mylist,n):
    return mylist[n:] + mylist[:n]

if __name__=="__main__":
    app = QApplication(sys.argv)
    main = Main()
    main.show()

    sys.exit(app.exec())
