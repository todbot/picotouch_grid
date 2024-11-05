import time, random
from supervisor import ticks_ms
import board, busio
import rainbowio
import usb_midi
import neopixel
import touchio
import displayio
import audiopwmio, audiomixer
import adafruit_mpr121
from adafruit_debouncer import Debouncer, Button
import adafruit_displayio_ssd1306

print("Hello World!")
displayio.release_displays()

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
i2c = busio.I2C(scl=scl_pin, sda=sda_pin, frequency=1_000_000)

time.sleep(1)
print("i2c scan: ",end=''); i2c.try_lock(); print(["%02x" % a for a in i2c.scan()]); i2c.unlock()

dw,dh = 128,32
display_bus = displayio.I2CDisplay(i2c, device_address=0x3c )
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=dw, height=dh, rotation=180)

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


dim_by = 10
dt0 = 0
dt1 = 0
dt2 = 0

playdebug = True
do_usb_midi = True
do_serial_midi = False

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

def mpr_to_keynum(i,j):
    if j<2: return None
    return (11-j+0)+(i+0)*10

def padnum_to_keynum(n):
    # padnum 0-9 = keys 0-9, padnum 10,11 = sliderA top
    # padnum 12-20 = keys 10-18, padnum 21,22 = sliderA bot
    row = n // 12
    if row > 9 : return None
    col = n % 12
    return row*10 + col

def padnum_to_keyxy(n):
    # padnum 0-9 = keys 0-9, padnum 10,11 = sliderA top
    # padnum 12-20 = keys 10-18, padnum 21,22 = sliderA bot
    row = n % 12
    if row > 9 : return None
    col = n // 12
    return (row,col)

octave = 3
def keynum_to_note(keynum):
    r,c = keynum // 10, keynum % 10  # fixme hardcoded vals
    r = 3 - r  # go from bottom to top
    note = r * 10 + c
    return note + (octave*12)

def keynum_to_scalenote(keynum):
    scale = ( 0, 2, 4, 5, 7, 9, 10,  12, 14, 16)  # mixolydian 7 notes + 3
    r,c = keynum // 10, keynum % 10  # fixme hardcoded vals
    r = 3 - r  # go from bottom to top
    n = scale[c]
    note = r * 12 + n
    return note + (octave*12)

def get_touched():
    _touched = [None] * 4
    for i in range(num_mprs):
        _touched[i] = mpr121s[i].touched_pins
    return _touched

def do_slider_fun(i,j):
    g, b = 0,0
    print("i,j", i,j)
    if (i,j) in sliderA:
        b = sliderA.index((i,j)) * 64 + 1
    elif (i,j) in sliderB:
        g = sliderB.index((i,j)) * 64 + 1

    leds.fill( (0,g,b) )

touched = get_touched()
last_touched = get_touched()

while True:

    leds[:] = [[max(i-dim_by,0) for i in l] for l in leds] # dim all by (dim_by,dim_by,dim_by)

    t0 = ticks_ms()

    # special-case touch pads (sliders & meta buttons)
    for i in range(num_touch_pads):
        touch = touch_pads[i]
        touch.update()
        if touch.rose:
            print('press   %2d' % i, "touch:",touch_ins[i].raw_value, touch_ins[i].threshold)
    dt0 = ticks_ms() - t0

    # actually scan the grid
    t = ticks_ms()
    touched = get_touched()
    dt1 = ticks_ms() - t0 - dt0

    # parse the grid
    for i in range(num_mprs):
        t = touched[i]
        lt = last_touched[i]
        if t != lt:
            #print(" t:", ''.join('%d' % v for v in t) )
            #print("lt:", ''.join('%d' % v for v in lt) )

            for j in range(len(t)):
                istouched = touched[i][j] and not last_touched[i][j]
                isreleased = last_touched[i][j] and not touched[i][j]
                keynum = mpr_to_keynum(i,j)

                if istouched:
                    if keynum is None: # not key, slider
                        do_slider_fun(i,j)
                    else:
                        leds[ keynum ] = rainbowio.colorwheel(time.monotonic()*50)
                        #play_note_on( keynum_to_note(keynum), 100)
                        play_note_on( keynum_to_scalenote(keynum), 100)
                if isreleased:
                    if keynum is None: # not key, slider
                        pass
                    else:
                        play_note_off(keynum_to_scalenote(keynum), 0)
        last_touched[i] = t

    dt2 = ticks_ms() - t0 - dt1
