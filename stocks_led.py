## DesignBuildDestroy.com Stock Indicator Lamp
## Copyright (C) 2020 DesignBuildDestroy.com
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
from datetime import datetime
import os
import threading
import requests
import json
import board
import busio
import RPi.GPIO as GPIO
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import neopixel

# Enter your free FinnHub API key here in quotes
FH_API_KEY = 'bqupqjvrh5rcjefat6p0'
# Add or change the stock symbols to your prference
stocks_list = ['AMZN', 'GOOGL', 'AAPL', 'FB', 'NFLX', 'TSLA','SPY','ROKU']


# ---- Thread Handler Routines for Light Effect ----
# led_args holds the R,G,B,Fade_Rate to be passed to the thread from main
led_args = [0, 0, 255, 0.01]
no_leds = False

def fade_leds(led_red, led_green, led_blue, led_fadespeed):
    # Raise and lower brightness of Neopixel at led_fadespeed rate
    # The rate is chosen by the percentage change of the stock faster for higher percentage change
    # - This is called by a separate thread to keep the lights going without the sleep state locking the code

    if (no_leds_check()):  # Turn off the lights - OLED only mode
        pixels.fill(0)
        pixels.show()
        return

    pixels.fill((led_red, led_green, led_blue, 0))
    for x in range(25, 99):
        pixels.brightness = x * .01
        pixels.show()
        time.sleep(led_fadespeed)
    for x in range(99, 25, -1):
        pixels.brightness = (x * .01)
        pixels.show()
        time.sleep(led_fadespeed)


def oled_thread(args):
    while True:
        fade_leds(args[0], args[1], args[2], args[3])
# ---- END Thread Handlers ----

# ---- Button Interrupt Handlers ----
def left_callback(channel):
    global stock_pick
    global keep_going
    global last_press
    keep_going = False    # Stop main OLED display loop

    # Move backwards through the list if you get to the first position
    # then set us to the last position so it appears to loop around
    if(stock_pick > 0):
        stock_pick -= 1
    else:
        stock_pick = len(stocks_list) - 1

    stock_symbol = stocks_list[stock_pick]

    update_screen_large(stock_symbol)    # Update the display
    last_press = time.time()    # Capture current timestamp


def right_callback(channel):
    global stock_pick
    global keep_going
    global last_press
    keep_going = False    # Stop main OLED display loop

    # Move backwards through the list if you get to the last position
    # then set us to the first position so it appears to loop around
    if(stock_pick < len(stocks_list) - 1):
        stock_pick += 1
    else:
        stock_pick = 0

    stock_symbol = stocks_list[stock_pick]

    update_screen_large(stock_symbol)    # Update the display
    last_press = time.time()    # Capture current timestamp


def update_screen_large(msgText=''):
    # Sort of resets the display, fixes issue with screen not updating as expected
    # disp.begin()
    # msgText should always be text, convert numbers to strings
    msgText = str(msgText)
    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)
    # Choose right size to fit on screen depending on string length
    if(len(msgText) > 5):
        # Use Medium Font
        (font_width, font_height) = font_medium.getsize(msgText)
        draw.text((disp.width // 2 - font_width // 2, disp.height //
                   2 - font_height // 2), msgText, font=font_medium, fill=255)
    else:
        # Use Large Font - mostly Stock Symbol name
        (font_width, font_height) = font_large.getsize(msgText)
        draw.text((disp.width // 2 - font_width // 2, disp.height //
                   2 - font_height // 2), msgText, font=font_large, fill=255)
    disp.image(image)
    disp.show()


def finnHub_quote(stock_symbol):
    # Get quote data from FinnHub API call
    # Make sure you find and set FH_API_KEY to your FinnHub API Key
    # See http://finnhub.io
    endpoint = 'https://finnhub.io/api/v1/quote'
    headers = {}
    # Define the payload
    payload = {'token': FH_API_KEY,
               'symbol': stock_symbol
               }
    # Make api request
    try:
        content = requests.get(url=endpoint, params=payload, headers=headers)
    except:
        return 0

    # JSON format is returned from API call
    data = content.json()
    # Check again for error, if stock symbol is non existant Finnhub will return {}
    # to us this would be an error state, avoid hammering Finnhub with bad data
    if (data == {}):
        return 0
    else:
        return data


def delay_with_check(seconds):
    # sleep for 1 second at a time while checking for user input and exit
    # sleep cycles if found
    for x in range(seconds):
        if keep_going == True:
            time.sleep(1)
        else:
            break

def no_leds_check():
	# Check to see if we are in the lighting time window
    # added this so the NeoPixel isn't on all night
    # only enable NeoPixel a bit before and after market hours M-F (central time)
    current_hour = datetime.now().hour
    current_day = datetime.now().strftime('%a')

    if (current_day == 'Sat') or (current_day == 'Sun'):
        return True   # No lights on weekend
    elif (current_hour < 8) or (current_hour > 15):
        return True   # No lights a bit before/after market hours (CST)
    else:
        return False  # Enable lighting


# ---- The MAIN section begins here! ----
# Default some variables
stock_price = 0
stock_pick = 0
stock_change = 0
stock_symbol = 'NONE'

# Used by interrupts to stop the rotating LCD screen and kick new stock pull
keep_going = True
last_press = 0  # Used for last key press timestamp

# ---- NeoPixel Setups ----
# Jewel 7 using GPIO18, physical pin 12, 7 LED's in the chain, full brightness
pixels = neopixel.NeoPixel(board.D18, 7, brightness=1,
                           auto_write=False, pixel_order=neopixel.GRBW)

# ---- Keypads Setups ----
gpio = GPIO
# Use GPIO pin numbering GPIO17 is physical pin 11, GPIO27 is pin 13
# Set GPIO pins being used to Inputs with pulldown
gpio.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
gpio.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# Set event triggers - if either pin is triggered high call their function
gpio.add_event_detect(17, GPIO.RISING, callback=left_callback, bouncetime=500)
gpio.add_event_detect(27, GPIO.RISING, callback=right_callback, bouncetime=500)

# ---- LCD Setups -----
# Initialize Display
i2c = busio.I2C(board.SCL, board.SDA)
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
# Create image object with width and height of the display we have
image = Image.new('1', (disp.width, disp.height))
# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)
# Define font and sizes to use
# You can use any TTF font by keeping the font file stored in the same folder
# The font included is freeware by Foyez Uddin
# I suggest finding your own font(s) and playing with the sizes below
font_path = os.path.dirname(os.path.realpath(__file__)) + '/'
font_large = ImageFont.truetype(font_path + 'Excluded.ttf', 28)
font_medium = ImageFont.truetype(font_path + 'Excluded.ttf', 24)


# Hardware Setup and Initilization complete, start the actual display work!!

# Launch Orb lighting thread
led_thread = threading.Thread(target=oled_thread, args=(led_args,))
led_thread.daemon = False
led_thread.start()


while True:
    # Main program loop - go forever
    # The interrupts for user selections will stop the inner while that updates stock/display data
    # this main outer loop is where we continously check how much time has passed since the last user selection
    # if it is >= 5 seconds then the user has basically accepted the item on screen
    # so we can continue "keepgoing" display loop with the newly selected stock

    current_time = time.time()

    if ((current_time - last_press) >= 3):
        # user likely made final selection start back up if not running
        last_press = 0
        keep_going = True

    while keep_going == True:
        # Get current quote from FinnHub for the selected Symbol
        # Get the symbol from the list based on user key selection
        stock_symbol = stocks_list[stock_pick]
        res = finnHub_quote(stock_symbol)    # Returns JSON result

        if (res == 0):
            # FinnHub API failed - for now just display error and quit the program
            # The OLED and NeoPixel hold their values after the program ends
            # So you will still see ERROR on screen even though the script died
            update_screen_large("ERROR")
            os._exit(0)    # suicide

        # FinnHub returns c as current price, pc as previous day close
        # Convert to float and format string
        stock_price = res['c']
        stock_price = '%0.2f' % (float(stock_price))

        # Calculate change in price
        stock_price_change = res['c'] - res['pc']
        stock_price_change = '%0.2f' % (float(stock_price_change))

        # Calculate current Percentage change
        per_change = float(stock_price_change) / float(stock_price) * 100
        per_change = '%0.2f' % (per_change)

        # Add + char to stock_price_change if positive for displaying and set LEDs
        # color scheme
        if(stock_price_change[0] == '-'):
            stock_change = str(stock_price_change)
            # RGB, keep current fade delay
            led_args[0] = 255 #R
            led_args[1] = 0   #G
            led_args[2] = 0   #B
        else:
            stock_change = '+' + (str(stock_price_change))
            # RGB, keep current fade delay
            led_args[0] = 0   #R
            led_args[1] = 255 #G
            led_args[2] = 0   #B

        # Percentage change abs value determins speed of LEDs fade
        if(abs(float(per_change)) > 2):
            led_args[3] = 0.01    # Fade delay speed
        else:
            led_args[3] = 0.04    # Fade delay speed

        # Display the rotating loop around the current Stock details
        # but check constantly if we should halt due to user keypress
        # probably a cleaner way to do this but this works just fine
        for x in range(8):
            if (keep_going == False):
                break
            update_screen_large(stock_symbol)
            delay_with_check(2)
            if (keep_going == False):
                break
            update_screen_large(stock_price)
            delay_with_check(3)
            if (keep_going == False):
                break
            update_screen_large(stock_change)
            delay_with_check(3)


#--- Loop forever ----
