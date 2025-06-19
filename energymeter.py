'''
Host code for Raspberry Pi Pico energy meter 
Jabez McClelland  
6/19/2025 - Version 0.0.1 - first commit

'''
import sys
import os
import xlsxwriter
import datetime as dt
import time
import numpy as np
import subprocess
import platform
import pathlib
import serial
import threading

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt6.uic import loadUiType

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

Ui_MainWindow, QMainWindow = loadUiType('energymeter.ui') 
Ui_WaveformWindow, QWaveformWindow = loadUiType('waveform.ui')
Ui_AboutWindow, QAboutWindow = loadUiType('AboutEnergymeter.ui')
vers = '0.0.1' 

port = "/dev/ttyACM0"
baudrate = 115200
ndata = 1001
ncyc = 3
c_volts = 24.315
c_amps = 0.1725


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
        cur = wavedata[2]
        self.ax = self.canvas.figure.subplots()
        self.ax2 = self.ax.twinx()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Voltage (V)",color=Vcolor)
        self.ax.tick_params(axis='y', colors=Vcolor)
        self.ax.axhline(y=0,color='black')
        self.ax2.set_ylabel("Current (A)",color=Acolor)       
        self.ax.set_title("Waveforms")
        self.ax.set_position([.12,.12,.75,.78])
        self.ax.tick_params(axis='both',direction='in')
        self.ax2.tick_params(axis='y',direction='in')
        self.ax.set_xlim(t[0],t[-1])        
        self.ax.plot(t,v,color=Vcolor)
        self.ax2.plot(t,cur,color=Acolor)
        self.ax2.tick_params(axis='y', colors=Acolor)
        self.canvas.draw()
        self.canvas.flush_events()
        self.show()

    def exit(self):
        self.destroy()  

class Main(QMainWindow, Ui_MainWindow):
    plotexists = False
    takedata = True
    datasaved = False
    def __init__(self):
        super(Main,self).__init__()
        self.setupUi(self)
        self.actionExitButton.triggered.connect(self.exit)
        self.menuBar.setStyleSheet("QMenu::item::selected {color: rgb(30,30,30);}")
        self.actionAbout.triggered.connect(self.openabout)
        self.takeReading.clicked.connect(self.single_reading)
        self.startButton.clicked.connect(self.start_data)
        self.stopButton.clicked.connect(self.stop_data)
        self.waveformButton.clicked.connect(self.show_waveform)
        cwd = str(pathlib.Path(__file__).parent.resolve())
        self.data_dest = cwd +'/energymeter_out.xlsx'
        self.dataSaveLabel.setText('Data will be saved in '+self.data_dest)
        self.changeDataButton.clicked.connect(self.change_data_dest)
        self.timeintervalBox.setText('1.0')
        self.currentPower.setText('--')
        self.avgPower.setText('--')
        self.kWh.setText('--')
        self.canvas = FigureCanvas(plt.Figure(figsize=(15, 6)))
        self.mainplot_layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.subplots()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Power (W)")       
        self.ax.set_title("Power Usage Log")
        self.ax.set_position([.15,.15,.75,.75])
        self.ax.tick_params(axis='both',direction='in')
        self.ax.set_ylim(0,100)
        self.ax.set_xlim(dt.datetime.now(),dt.datetime.now()+dt.timedelta(hours=2))
        self.rec_label.setText('')
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.dummy = False
        except:
            QMessageBox.warning(self,'Energy meter','No measurement module detected, simulating data')
            self.dummy = True 

    def openabout(self):
        self.aboutwin = About()

    def single_reading(self):
        if self.dummy:
            p = 100.0 + np.random.random_sample()
            avpower = '{:.1f}'.format(p)
        else:
            self.ser.write(b'po')
            time.sleep(0.5)
            avpower = self.ser.readline().decode('utf-8').strip()
            time.sleep(0.5)
 #           print(avpower)
        self.currentPower.setText(avpower+' W')
        return float(avpower)
        
    def start_data(self):
        x = threading.Thread(target=self.take_data, daemon=True)
        x.start()
        
    def take_data(self):
        self.takedata = True
        self.rec_label.setText('RECORDING')  
        self.wb = xlsxwriter.Workbook(self.data_dest)
        wbtimefmt = self.wb.add_format({'num_format': 'mmm d yyyy hh:mm:ss'})
        ws = self.wb.add_worksheet()
        ws.set_column(0,0,20)
        ws.set_column(1,3,15)
        ws.write(0,0,'Time')
        ws.write(0,1,'Power')
        ws.write(0,2,'Avg. Power')
        ws.write(0,3,'Energy')        
        times = []
        powers = []
        avpowers = []
        energies = []
        count = 0
        self.ax.cla()
        self.ax.set_xlabel("Time")
        self.ax.set_title("Power Usage Log")
        deltat = 0.1
        while self.takedata:
            try:
                interval = float(self.timeintervalBox.text())
            except:
                QMessageBox.warning(self,'Error','Invalid entry for time interval')
                break 
            count += 1
            elapsed_time = 0.0
            while elapsed_time < interval:
                time.sleep(deltat)
                QApplication.processEvents()
                if not self.takedata:
                    break
                elapsed_time += deltat
            if not self.takedata:
                break
            current_power = self.single_reading()
            times.append(dt.datetime.now())            
            powers.append(current_power)
            avpowers.append(sum(powers)/len(powers))
            if count == 1:
                energies.append(powers[0]*interval*0.001/3600.)
            else:
                energies.append(sum(powers)*interval*0.001/3600.)
            self.currentPower.setText("{:3.1f}".format(current_power)+' W')
            self.avgPower.setText("{:3.1f}".format(avpowers[-1])+' W')
            self.kWh.setText("{:3.3f}".format(energies[-1])+' kWh')
            ws.write(count,0,times[-1],wbtimefmt)
            ws.write(count,1,powers[-1])
            ws.write(count,2,avpowers[-1])
            ws.write(count,3,energies[-1])         
            self.plot_data(data=[times,powers])

    def plot_data(self,data=[[0],[0]]):
#        if self.plotexists:
#            self.lin.remove()
        self.lin, = self.ax.plot(data[0],data[1],color='blue')
#        self.ax.set_ylim(bottom=0)
        self.canvas.draw()
        self.canvas.flush_events()
        self.plotexists = True    
        
    def stop_data(self):
        self.takedata = False
        self.rec_label.setText('')
        qbox = QMessageBox.question(self,'Energy meter','Do you want to save data?',QMessageBox.StandardButton.Yes,QMessageBox.StandardButton.No)
        if self.plotexists:
            if qbox == QMessageBox.StandardButton.Yes:
                self.wb.close()
                self.datasaved = True
                QMessageBox.information(self,'Energy meter','Acquisition finished.\nData saved in'+self.data_dest)
        else:
            QMessageBox.information(self,'Energy meter','Please record some data first.')    

    def show_waveform(self):
        if not self.dummy:     
            self.ser.write(b'wa')
        volts = np.empty(ndata)
        amps = np.empty(ndata)
        dt = ncyc/60./ndata
        t = dt*np.arange(ndata)
        if not self.dummy:
            for i in range(ndata):
                result = self.ser.read(2)
                volts[i] = int.from_bytes(result,sys.byteorder)
            time.sleep(0.05)            
            for i  in range(ndata):
                result = self.ser.read(2)
                amps[i] = int.from_bytes(result,sys.byteorder)
            volts = [163.45*(float(x) - sum(volts)/ndata)*3.3/65536. for x in volts]
            amps = [-12.562*(float(x) - sum(amps)/ndata)*3.3/65536. for x in amps]
        else:
            for i in range(ndata):
                volts[i]  = 169.99*(1 + 2*np.random.random_sample()/10.)*np.sin(2*np.pi*t[i]*60)
                amps[i] = 1.206*(1 + 2*np.random.random_sample()/10.)*np.sin(2*np.pi*t[i]*60)
        wavedata = [t,volts,amps]
        self.wfwindow = ShowWaveform(wavedata)

    def change_data_dest(self):
        fileName, _ = QFileDialog.getSaveFileName(self,"Select data destination file","./","Excel files (*.xlsx)")
        if fileName:
            strfN = str(fileName)
            if strfN[-5:] != '.xlsx':
                strfN = strfN + '.xlsx'
            self.data_dest = strfN
            self.dataSaveLabel.setText('Data will be saved in ' + strfN) 
            
    def exit(self):
        sys.exit()

def simpson(signal,dt):
    n = len(signal) #n must be odd!
    integral = (dt/3) * (signal[0] + 2*np.sum(signal[:n-2:2]) \
            + 4*np.sum(signal[1:n-1:2]) + signal[n-1])
    return integral

def rotate(mylist,n):
    return mylist[n:] + mylist[:n]

if __name__=="__main__":
    app = QApplication(sys.argv)
    main = Main()
    main.show()

    sys.exit(app.exec())
