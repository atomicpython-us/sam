import network
import time
from secrets import WIFI_SSID, WIFI_PASSWORD

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

print("Connecting...")
while not wlan.isconnected():
    print(".", end="")
    time.sleep(0.25)

ip = wlan.ifconfig()[0]
print("Connected! IP:", ip)

from sam import SAM
sam = SAM(pin=0)
sam.say("connected. " + ip)
