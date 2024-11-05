# picotouch_grid_mpr/test3.py
# @todbot - 10 Apr 2023
import time, random
from supervisor import ticks_ms
import board, busio
import rainbowio
import usb_midi
import neopixel
import touchio
import audiopwmio, audiomixer
import adafruit_mpr121
from adafruit_debouncer import Debouncer, Button

print("Hello World!")

neopixel_pin = board.GP28
midi_rx_pin = board.GP21
midi_tx_pin = board.GP20
audio_pin = board.GP13
scl_pin = board.GP15
sda_pin = board.GP14
touch_pins = (board.GP2, board.GP3, board.GP4, board.GP5, board.GP6, board.GP7,  # slider
              board.GP8, board.GP9, board.GP10 ) # down, enter, up


#
#
#
#
class PicoTouchGridKeypad:
    num_mprs = 4
    mpr121_addrs = (0x5a, 0x5b, 0x5c, 0x5d) # class vars because cannot have multiple Keypads
    mpr121s = [None] * num_mprs
    touched = [None] * num_mprs
    last_touched = touched.copy()
    sliderA =  ( (1,1), (1,0), (0,1), (0,0) )
    sliderB =  ( (3,1), (3,0), (2,1), (2,0) )

    def __init__(self,i2c):
        for i in range(self.num_mprs):
            self.mpr121s[i] = adafruit_mpr121.MPR121(i2c, address=self.mpr121_addrs[i])

    def sliderA_pos(self):
        pass

    def sliderB_pos(self):
        pass

    def update(self):
        for i in range(num_mprs):
            self.touched[i] = self.mpr121s[i].touched_pins

        touch_change = False
        for i in range(num_mprs):
            if self.touched[i] != self.last_touched[i]:
                self.last_touched[i] = self.touched[i]
                touch_change = True
            for j in range(len(self.touched[i])):
                if self.touched[i][j]:
                    if j>=2:
                        leds[ (11-j)+i*10 ] = rainbowio.colorwheel(time.monotonic()*50)
                    else:
                        if (i,j) in sliderA:
                            b = sliderA.index((i,j)) * 64 + 1
                        elif (i,j) in sliderB:
                            g = sliderB.index((i,j)) * 64 + 1

                        leds.fill( (0,g,b) )



        return []


i2c = busio.I2C(scl=scl_pin, sda=sda_pin)

keypad = PicoTouchGridKeypad(i2c)

while True:
    key_events = keypad.get_events()
    for (key,pressed) in key_events:
        pass




####################################

sliderA =  ( (1,1), (1,0), (0,1), (0,0) )
sliderB =  ( (3,1), (3,0), (2,1), (2,0) )

#i2c = board.STEMMA_I2C()  # 5-6 millis to read all four
#i2c = busio.I2C(scl=board.SCL1, sda=board.SDA1, frequency=400_000)  # 4 millis to read all four
i2c = busio.I2C(scl=scl_pin, sda=sda_pin)

time.sleep(1)
print("i2c scan:")
i2c.try_lock()
print(["%02x" % a for a in i2c.scan()])
i2c.unlock()
time.sleep(1)

midi_usb_out = usb_midi.ports[1]
midi_uart = busio.UART(tx=midi_tx_pin, rx=midi_rx_pin, baudrate=31250) # timeout=midi_timeout)

num_voices = 2
audio = audiopwmio.PWMAudioOut(audio_pin)
mixer = audiomixer.Mixer(voice_count=num_voices, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer) # attach mixer to audio playback

touch_ins = []  # for debug
touch_pads = []
for pin in touch_pins:
    touchin = touchio.TouchIn(pin)
    #touchin.threshold += touch_threshold_adjust
    touch_pads.append( Button(touchin, value_when_pressed=True))
    touch_ins.append(touchin)  # for debug
num_touch_pads = len(touch_pads)

num_mprs = 4
mpr121_addrs = (0x5a, 0x5b, 0x5c, 0x5d)
mpr121s = [None] * num_mprs
for i in range(num_mprs):
    mpr121s[i] = adafruit_mpr121.MPR121(i2c, address=mpr121_addrs[i])

leds = neopixel.NeoPixel(neopixel_pin, 40, brightness=0.1)
leds.fill(0x666666)

touched = [None] * num_mprs
last_touched = touched.copy()

dim_by = 5
while True:
    for i in range(num_touch_pads):
        touch = touch_pads[i]
        touch.update()
        if touch.rose:
            print('press   %2d' % i, "touch:",touch_ins[i].raw_value, touch_ins[i].threshold)

    t = ticks_ms()
    for i in range(num_mprs):
        touched[i] = mpr121s[i].touched_pins
    dt = ticks_ms() - t

    touch_change = False
    for i in range(num_mprs):
        if touched[i] != last_touched[i]:
            last_touched[i] = touched[i]
            touch_change = True
            for j in range(len(touched[i])):
                if touched[i][j]:
                    if j>=2:
                        leds[ (11-j)+i*10 ] = rainbowio.colorwheel(time.monotonic()*50)
                    else:
                        g, b = 0,0
                        print("i,j", i,j)
                        if (i,j) in sliderA:
                            b = sliderA.index((i,j)) * 64 + 1
                        elif (i,j) in sliderB:
                            g = sliderB.index((i,j)) * 64 + 1

                        leds.fill( (0,g,b) )

    if touch_change:
        print("t0:", ["%d" % t for t in reversed(touched[0])], "dt:",dt )
        print("t1:", ["%d" % t for t in reversed(touched[1])] )
        print("t2:", ["%d" % t for t in reversed(touched[2])] )
        print("t3:", ["%d" % t for t in reversed(touched[3])] )

    #n = random.randint(0,39)
    #c = rainbowio.colorwheel(time.monotonic()*50)
    #leds[ n ]  = c
    ##print("hi %2d %06x" %(n,c))


    leds[:] = [[max(i-dim_by,0) for i in l] for l in leds] # dim all by (dim_by,dim_by,dim_by)
