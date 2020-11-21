#!/bin/bash
# Install required modules for stocks_led.py
# DesignBuildDestroy.com 2020
#

#Install Repo Packages
sudo apt-get -y install python-smbus
sudo apt-get -y install i2c-tools
sudo apt-get -y install python3-rpi.gpio
sudo apt-get -y install libopenjp2-7-dev
sudo apt-get -y install libtiff-dev

#Install PIP3
sudo apt-get -y install python3-pip
sudo python3 -m pip install upgrade pip

#Install Pip Packages
sudo python3 -m pip install requests
sudo python3 -m pip install pillow
sudo python3 -m pip install adafruit-circuitpython
sudo python3 -m pip install adafruit-circuitpython-ssd1306
sudo python3 -m pip install adafruit-circuitpython-neopixel
sudo python3 -m pip install RPi-GPIO # probably already installed via apt-get above

echo
echo "DONE!!"
echo "1) You must enable i2c autodetect and set timezone use: sudo raspi-config"
echo "2) Remember to edit stocks_led.py to enter your Finnhub.io API key and add stock list"
echo
echo "Visit https://DesignBuildDestroy.com for more information!"
