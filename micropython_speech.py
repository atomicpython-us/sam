from sam import SAM

sam = SAM(pin=0)

speech_part_1 = "Hello, I am MicroPython. It sure is great to get out of that bag." 

speech_part_2 = "Unaccustomed as I am to public speaking, I'd like to share with you a maxim I thought of, the first time I met an IBM Mainframe. NEVER TRUST A COMPUTER YOU CAN'T LIFT."

speech_part_3 = "Obviously, I can talk, but right now I'd like to sit back and listen. So, it's with considerable pride that I introduce a man who's been like a father to me... Kevin McAleer. Like, Subscribe"

sam.save_wav(speech_part_1, "mac_speech_part_1.wav")
sam.save_wav(speech_part_2, "mac_speech_part_2.wav")
sam.save_wav(speech_part_3, "mac_speech_part_3.wav")