import time, random
import board, busio
import rainbowio
import neopixel
import adafruit_mpr121
from supervisor import ticks_ms

i2c = board.STEMMA_I2C()  # 5-6 millis to read all four
#i2c = busio.I2C(scl=board.SCL1, sda=board.SDA1, frequency=400_000)  # 4 millis to read all four

time.sleep(1)
print("i2c scan:")
i2c.try_lock()
print(["%02x" % a for a in i2c.scan()])
i2c.unlock()

#i2c = busio.I2C(scl=board.GPxx, sda=board.GPxx)
mpr121_addrs = (0x5a, 0x5b, 0x5c, 0x5d)
mpr121s = [None] * len(mpr121_addrs)
for i in range(len(mpr121_addrs)):
    mpr121s[i] = adafruit_mpr121.MPR121(i2c, address=mpr121_addrs[i])

leds = neopixel.NeoPixel(board.RX, 40, brightness=0.1)
leds.fill(0xff00ff)

dim_by = 3
while True:
    t = ticks_ms()
    touched0 = mpr121s[0].touched_pins
    touched1 = mpr121s[1].touched_pins
    touched2 = mpr121s[2].touched_pins
    touched3 = mpr121s[3].touched_pins
    dt = ticks_ms() - t

    n = random.randint(0,39)
    c = rainbowio.colorwheel(time.monotonic()*50)
    #print("hi %2d %06x" %(n,c))
    print("t0:", ["%d" % t for t in reversed(touched0)], "dt:",dt )
    print("t1:", ["%d" % t for t in reversed(touched1)] )
    print("t2:", ["%d" % t for t in reversed(touched2)] )
    print("t3:", ["%d" % t for t in reversed(touched3)] )
    leds[ n ]  = c
    leds[:] = [[max(i-dim_by,0) for i in l] for l in leds] # dim all by (dim_by,dim_by,dim_by)
    time.sleep(0.1)



######################

import time, random
import board
import rainbowio
import neopixel

leds = neopixel.NeoPixel(board.RX, 40, brightness=0.2)

leds.fill(0xff00ff)
while True:
    n = random.randint(0,39)
    c = rainbowio.colorwheel(time.monotonic()*50)
    print("hi",n,c)
    leds[ n ]  = c
    time.sleep(0.3)



# synthio_test0.py -- playing with new synthio
# 4 Apr 2023 - @todbot / Tod Kurt

import time, math
import board, audiobusio
import synthio
import ulab.numpy as np
import random

# pimoroni pico dv board
#lck_pin, bck_pin, dat_pin  = board.GP28, board.GP27, board.GP26
# qtpy rp2040 to cheapie PCM5102 board
lck_pin, bck_pin, dat_pin  = board.MISO, board.MOSI, board.SCK

audio = audiobusio.I2SOut(bit_clock=bck_pin, word_select=lck_pin, data=dat_pin)

SAMPLE_SIZE=128
VOLUME=4000

sine = np.array(np.sin(np.linspace(0, 2*np.pi, SAMPLE_SIZE, endpoint=False)) * VOLUME, dtype=np.int16)
sawtooth = np.linspace(VOLUME, -VOLUME, num=SAMPLE_SIZE, dtype=np.int16)
waveform = np.zeros(SAMPLE_SIZE, dtype=np.int16)  # intially all zeros (silence)
waveforms = (sine, sawtooth)

synth = synthio.Synthesizer(sample_rate=24000, waveform=waveform)
audio.play(synth)

while True:
    time.sleep(0.3)
    waveform[:] = random.choice(waveforms) # pick a waveform randomly
    time.sleep(0.3)
    notes = (random.randint(30,60), random.randint(30,60) ) # pick notes randomly
    print("playing notes:", notes)
    synth.release_all_then_press( notes )



##################################

# synthio_test1.py -- playing with new synthio
# 5 Apr 2023 - @todbot / Tod Kurt
#
# Does a rudimentary Attack/Sustain/Release amplitude envelope on played notes
# with wavetable morphing during sustain

import time
import board, audiobusio
import random

from synth_player import SynthPlayer

# knobs to control things
import analogio
knob2 = analogio.AnalogIn(board.A2)
knob3 = analogio.AnalogIn(board.A3)

chords = (
    (0, 4, 7, 12),    # 0 major
    (0, 3, 7, 10),    # 1 minor 7th
    (0, 3, 6, 3),     # 2 Diminished
    (0, 5, 7, 12),    # 3 Suspended 4th
    (0, 12, 0, -12),  # 4 octaves
    (0, 12, 24, -12), # 5 octaves 2
    (0, -12, -12, 0), # 6 octaves 3 (bass)
    (0, 0, 0, 0),     # 7 root
)

octave_range = 2
lowest_note = 24  # C1
base_note = 0
chord_num = 3

# pimoroni pico dv board
#lck_pin, bck_pin, dat_pin  = board.GP28, board.GP27, board.GP26

# qtpy rp2040 to cheapie PCM5102 board
lck_pin, bck_pin, dat_pin  = board.MISO, board.MOSI, board.SCK

audio = audiobusio.I2SOut(bit_clock=bck_pin, word_select=lck_pin, data=dat_pin)

player = SynthPlayer()

audio.play(player.synth)

last_note_time = time.monotonic()

while True:

    player.update()

    if time.monotonic() - last_note_time > 2:  # every 2 seconds, play new notes
        last_note_time = time.monotonic()
        #player.note_off_all()
        base_note = random.choice( chords[chord_num] )
        notes = [ base_note + lowest_note + 12*1 + chords[chord_num][0], ]
        for i in range(2):
            note = random.choice(chords[chord_num]) + base_note
            note += 12 * random.randint(0,octave_range)
            note += lowest_note
            notes.append( note )
        print("playing notes:", notes)
        player.note_on(notes)
