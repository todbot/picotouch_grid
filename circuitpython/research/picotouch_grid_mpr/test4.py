# picotouch_grid_mpr/test4.py
# @todbot - 11 Apr 2023
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

sliderA =  ( (1,1), (1,0), (0,1), (0,0) )
sliderB =  ( (3,1), (3,0), (2,1), (2,0) )

#i2c = busio.I2C(scl=scl_pin, sda=sda_pin)
i2c = busio.I2C(scl=scl_pin, sda=sda_pin, frequency=400_000)

time.sleep(1)
print("i2c scan: ",end=''); i2c.try_lock(); print(["%02x" % a for a in i2c.scan()]); i2c.unlock()
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


dim_by = 30
dt0 = 0
dt1 = 0
dt2 = 0

def play_note_on(note, vel):  #
    """Callback for sequencer when note should be tured on"""
    if playdebug: print("on : n:%3d v:%3d" % (note,vel), end="\n" )
    midi_msg = bytearray([0x90, note, vel])  # FIXME
    if do_usb_midi:
        midi_usb_out.write( midi_msg )
    if do_serial_midi:
        midi_uart.write( midi_msg )

def play_note_off(note, vel):  #
    #if on: # FIXME: always do note off to since race condition of note muted right after playing
    if playdebug: print("off: n:%3d v:%3d" % (note,vel), end="\n" )
    midi_msg = bytearray([0x80, note, vel])  # FIXME
    if do_usb_midi:
        midi_usb_out.write( midi_msg )
    if do_serial_midi:
        midi_uart.write( midi_msg )


def xy_to_n(x,y):
    return x + y*10

def mpr_to_n(i,j):
    return (11-j+0)+(i+0)*10

def padnum_to_keynum(n):
    # padnum 0-9 = keys 0-9, padnum 10,11 = sliderA top
    # padnum 12-20 = keys 10-18, padnum 21,22 = sliderA bot
    row = n % 12
    if row > 9 : return -1
    col = n // 12
    return (row,col)

#keys_pressed = 0

touched_bits = [0,0,0,0]
last_touched_bits = [0,0,0,0]
pads_pressed = [False] * (12*4)

while True:

    leds[:] = [[max(i-dim_by,0) for i in l] for l in leds] # dim all by (dim_by,dim_by,dim_by)

    t0 = ticks_ms()

    for i in range(num_touch_pads):
        touch = touch_pads[i]
        touch.update()
        if touch.rose:
            print('press   %2d' % i, "touch:",touch_ins[i].raw_value, touch_ins[i].threshold)
    dt0 = ticks_ms() - t0

    t = ticks_ms()
    for i in range(num_mprs):
        #touched[i] = mpr121s[i].touched_pins
        touched_bits[i] = mpr121s[i].touched()  # bitfield of keys touched
    dt1 = ticks_ms() - t0 - dt0

    touch_change = False
    key_events = []
    for i in range(num_mprs):
        t = touched_bits[i]
        lt = last_touched_bits[i]
        last_touched_bits[i] = t
        if t != lt:
            ispress = t & ~lt  # release = lt & ~t
            for j in range(12): # for each of the pins
                padnum = i*12 + j
                last_val = pads_pressed[padnum]
                new_val  = ispress & (1<<(11-j)) !=0
                if new_val != last_val: key_events.append( (padnum,new_val) )
                pads_pressed[padnum] = new_val
                if new_val:  # pressed

            #print(f'{i:d} p:{press:012b}') # , r:{release:012b}  ')
            #print( "".join([ "%d" % k for k in pads_pressed]) )
    if key_events:
        print("key_events:",key_events)
        for (padnum,press) in key_events:
            if press: leds[ padnum ] = 0xff00ff

    # touch_change = False
    # for i in range(num_mprs):
    #     if touched[i] != last_touched[i]:
    #         last_touched[i] = touched[i]
    #         touch_change = True
    #         for j in range(len(touched[i])):
    #             if touched[i][j]:
    #                 if j>=2:
    #                     #print("mpr_to_xy:", mpr_to_xy(i,j))
    #                     n00 = mpr_to_n(i,j)
    #                     #n00 = min(max((11-j+0)+(i+0)*10, 0),39)
    #                     # nz0 = min(max((11-j+1)+(i+0)*10, 0),39)
    #                     # nz1 = min(max((11-j-1)+(i+0)*10, 0),39)
    #                     # n0z = min(max((11-j+0)+(i+1)*10, 0),39)
    #                     # n1z = min(max((11-j-0)+(i-1)*10, 0),39)
    #                     leds[ n00 ] = rainbowio.colorwheel(time.monotonic()*50)
    #                     # leds[ nz0 ] = 0x111111
    #                     # leds[ nz1 ] = 0x111111
    #                     # leds[ n0z ] = 0x111111
    #                     # leds[ n1z ] = 0x111111
    #                 else:
    #                     g, b = 0,0
    #                     print("i,j", i,j)
    #                     if (i,j) in sliderA:
    #                         b = sliderA.index((i,j)) * 64 + 1
    #                     elif (i,j) in sliderB:
    #                         g = sliderB.index((i,j)) * 64 + 1

    #                     leds.fill( (0,g,b) )

    # dt2 = ticks_ms() - t0 - dt1

    # if touch_change:
    #     print("t0:", ["%d" % t for t in reversed(touched[0])], "dt:",dt0,dt1,dt2 )
#        print("t1:", ["%d" % t for t in reversed(touched[1])] )
#        print("t2:", ["%d" % t for t in reversed(touched[2])] )
#        print("t3:", ["%d" % t for t in reversed(touched[3])] )

    #n = random.randint(0,39)
    #c = rainbowio.colorwheel(time.monotonic()*50)
    #leds[ n ]  = c
    ##print("hi %2d %06x" %(n,c))
