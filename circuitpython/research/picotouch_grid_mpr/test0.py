import time, random
import board, busio
import rainbowio
import neopixel
import adafruit_mpr121

i2c = board.STEMMA_I2C()

time.sleep(1)
print("i2c scan:")
i2c.try_lock()
print(["%02x" % a for a in i2c.scan()])
i2c.unlock()

#i2c = busio.I2C(scl=board.GPxx, sda=board.GPxx)
mpr121 = adafruit_mpr121.MPR121(i2c)

leds = neopixel.NeoPixel(board.RX, 40, brightness=0.1)
leds.fill(0xff00ff)

dim_by = 3
while True:
    touched = mpr121.touched_pins
    n = random.randint(0,39)
    c = rainbowio.colorwheel(time.monotonic()*50)
    print("hi",n,c, "touched:",touched)
    leds[ n ]  = c
    leds[:] = [[max(i-dim_by,0) for i in l] for l in leds] # dim all by (dim_by,dim_by,dim_by)
    time.sleep(0.3)
