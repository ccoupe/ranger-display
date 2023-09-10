# main.py
from mqtt_as import MQTTClient, config
import uasyncio as asyncio
from mqtt_local import wifi_led, blue_led

from machine import Pin, SoftI2C
import sh1106
from writer import Writer
import deja24

i2c = SoftI2C(scl=Pin(9), sda=Pin(8), freq=400000)
display = sh1106.SH1106_I2C(128, 64, i2c, addr=0x3c)
wri = Writer(display, deja24)

from machine import Pin
from time import sleep
import sys

print(f"Platform: {sys.platform} Libpath: {sys.path}")
print('config', config)
from messagedevice import MessageDevice


def callback(topic, msg, retained):
    topstr = topic.decode()
    payload = msg.decode()
    #print('got:', topstr, payload)
    if topic == config['Msg_Topic']:
        Screen.display_text(payload)
    elif topic == config['Cmd_Topic']:
        pass
    elif topic == config['Cmd_Ranger']:
        pass

async def conn_han(client):
    await client.subscribe(config['Msg_Topic'], 1)
    await client.subscribe(config['Cmd_Topic'], 1)
    if config['HAVE_RANGER']:
        await client.subscribe(config['Cmd_Ranger'], 1)
    Screen.display_text("I'm Awake")

async def main(client):
    Screen.display_text("Starting")
    await client.connect()
    #n = 0
    while True:
        await asyncio.sleep(5)
        #print('publish', n)
        # If WiFi is down the following will pause for the duration.
        #await client.publish('result', '{}'.format(n), qos = 1)
        #n += 1

config['subs_cb'] = callback
config['connect_coro'] = conn_han

MQTTClient.DEBUG = True  # Optional: print diagnostic messages
client = MQTTClient(config)
print('mqtt setup')
Screen = MessageDevice(config, tkwindow=display, tkclose=wri)
print('starting loop')
try:
    asyncio.run(main(client))
finally:
    client.close()  # Prevent LmacRxBlk:1 errors