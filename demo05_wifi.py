import network
import time
from secrets import WIFI_SSID, WIFI_PASSWORD
from sam import SAM

sam = SAM(pin=0)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

print("Connecting...")
while not wlan.isconnected():
    print(".", end="")
    time.sleep(0.25)
    
ip_address = wlan.ifconfig()[0]

print("Connected! IP:", ip_address)
sam.say(f"connected to {ip_address}", chunk_words=1)
