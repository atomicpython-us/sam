from sam import SAM, VOICES

sam = SAM(pin=0)
print(f" sam info - {sam.info()}")

# Demo 2

# Robot voice: low pitch, narrow mouth
sam.set_pitch(40)
sam.set_mouth(150)
sam.set_throat(90)
sam.say("i am a robot")
sam.save_wav("i am a robot", "robot_voice.wav")

# High-pitched voice
sam.set_pitch(96)
sam.set_mouth(128)
sam.set_throat(128)
sam.say("hello there")
sam.save_wav("hello there", "high_pitch_voice.wav")


for name in VOICES:                                                           
  sam.set_voice(name)
  print(f"I am {name}")
  sam.say("I am " + name) 
  sam.save_wav("I am " + name, f"{name}_voice.wav")

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
sam.save_wav(f"connected to {ip_address}", "wifi_connected.wav")

