## Raspberry Pi Pico-based True Energy Meter for Appliances

This project couples a simple circuit with a Raspberry Pi Pico to capture the voltage and current waveforms of the power supplying any appliance, allowing a true, cycle-averaged measure of the power consumption.

The circuit uses a step-down transformer and a voltage divider to measure the voltage, and an Amploc current sensor to measure the current.  These signals are amplified and offset to the 0 - 3.3 V input range of the Pico ADCs.  Waveform data is captured over 3 cycles of the 60 Hz AC line supply, and the product of these is integrated.  Phase differences (as would happen with a motor), current spikes (within reason), etc, are automatically captured and integrated, so the measured  power is as correct as possible.

The Pico is programmed using Micropython.  Voltages on the two ADCs are collected, the power is calculated, and the value is sent to an LCD display.  On a command from a host computer connected via USB, either the power value or a full 3-cycle waveform is transmitted for further processing and display.  The host code is written in Python, with a Qt6-based GUI that displays a chart of the power consumption vs. time, as well as numerical displays of the current power, the average power since starting acquisition, and the total energy consumed. 
 
![](EnergymeterScreenshot.png "Screenshot of dehumidifier energy consumption")

#### Circuit description
AC power comes in via a male power receptacle and flows directly to the appliance via a female power socket. One of the wires carrying current passes through an [Amploc AMP25 current sensor](https://amploc.com/products/amp25-open-loop-hall-effect-sensor), which provides a 1.57 V to 3.42 V signal for currents from -25 A to +25 A.  The AC line voltage is also connected to a small step-down transformer producing 13.6 VAC.  I used something salvaged from an old phone system, but any small transformer that gets you down to below 20 V or so will work. 
![](schematic.png)
The voltage from the transformer is further divided down and offset using one of the op amps in a LM358 chip, and fed to ADC0 on the Pico.  The AMP25 output is similarly amplified and offset using the other half of the LM358 to match the ADC range, and fed to ADC1 on the Pico.  5 V power for the Pico, the AMP25, and the LM358 is provided by a small HLK-PM01 supply on board.  

#### Construction notes
Most of the circuit is on a circuit board, detailed in this [KiCAD file](./Pico_energymeter_v2.kicad_pro).
  
<img src="./3D_CAD_view.png" alt="3D CAD view" width="500"/>  

Everything is mounted in a plastic box, with the LCD 1602 display mounted in the lid. The display mount uses a home-made 3D-printed bezel (step file [here](./LCD1602bezel.step)). A short microUSB extender cable is used to bring the Pico's USB connection to a socket on the box wall.

<img src="./Box_open.png" alt="Box, open" width="400"/>  <img src="./Energymeter_box.jpg" alt="Bax, closed" width="400"/>
 

#### Pico code

The Micropython code that runs on the Pico is contained in the file powmon_picocode.py.  This needs to be saved on the Pico as main.py.  The code makes use of a LCD1602 I2C Python library (of which there are many) downloaded from https://github.com/liyuanhe211/Micropython_LCD1602_LCD2004_I2C_Lib.  The file lib_lcd1602_2004_with_i2c.py from that site is included here under the name lyhlcd1602.py, and must also be stored on the Pico.  The easiest way to put these files on the Pico is by using [Thonny](https://thonny.org/).  

The code does the usual setup for LED, I2C, etc and sets up arrays for voltage and current measurements with 1001 points each.  The nominal time between points for 3 cycles of 60 Hz is 3/60/1001 =  49.95 $`\mu`$s.  However, there will be inherent small delays so it is necessary to do a measurement to determine empirically how many $`\mu`$s to tell Micropython to wait between each point in order to ensure exactly 3 cycles with 1001 points.  The procedure for this is described below.  

The main while-loop of the code cycles every 0.1 sec.  On each cycle it reads 1001 points from the ADCs and calculates the power by multiplying the voltage and the current and integrating via Simpson's rule.  The calibration factor is determined empirically by plugging in a 100 W light bulb and determining the actual power by measuring the voltage and current with a multimeter (the light bulb is assumed to be a fully resistive load). Note the calibration factor is negative because the current measurement is inverted by the op amp circuit.

On each cycle the code also reads two bytes from the USB serial port.  These two bytes represent requests from the host code.  If b'po' is transmitted this is a request for a power measurement, and the Pico code sends back a string version of the most recent power measurment.  If b'wa' is transmitted this is a request for the waveform, and the Pico code does a fresh measurement of the ADCs, packs the data bytes into a structure using `struct.pack()` and transmits these back to the host via `sys.stdout.buffer.write()`.

#### Host code
The host code was developed on a Linux system using Python 3.13.3.  I recommend using pyenv to set up a virtual environment specifying this version of Python to run it.  The required libraries are listed in `requirements.txt` and can be installed via `pip install requirements.txt`. The code should be failry easily ported to Windows or MacOS with a few minor adjustments.  Usage should be pretty self explanatory -  Click "Take reading" to get a measure of the power, click "Start recording" to begin logging the power, and click "Stop recording" when you want to stop. You will be asked whether you want to save the data.  Click "Show waveform" if you want to see what the volage and current waveforms look like, and click "Change data destination" if you want to save the data somehwere other than the default location. 


    