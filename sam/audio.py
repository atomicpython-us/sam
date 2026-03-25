"""
SAM Audio Output: PWM-based audio driver for MicroPython.
"""

SAMPLE_RATE = 8000

PWM_FREQ_PICO = 62500
PWM_FREQ_ESP32 = 40000


class PWMAudio:
    def __init__(self, pin=0, sample_rate=SAMPLE_RATE):
        self.pin_num = pin
        self.sample_rate = sample_rate
        self._pwm = None
        self._timer = None
        self._playing = False

    def _init_pwm(self):
        from machine import Pin, PWM
        pin = Pin(self.pin_num, Pin.OUT)
        self._pwm = PWM(pin)
        try:
            import sys
            if 'esp32' in sys.platform:
                self._pwm.freq(PWM_FREQ_ESP32)
            else:
                self._pwm.freq(PWM_FREQ_PICO)
        except:
            self._pwm.freq(PWM_FREQ_PICO)
        self._pwm.duty_u16(32768)

    def play(self, buffer):
        self._init_pwm()
        self._playing = True

        try:
            self._play_timer(buffer)
        except Exception as e:
            print("Timer failed, using loop:", e)
            self._play_loop(buffer)

    def _play_timer(self, buffer):
        from machine import Timer
        import micropython, time

        buf = buffer
        buf_len = len(buf)
        pwm = self._pwm
        self._buf_pos = 0

        timer = Timer(-1)
        self._timer = timer

        @micropython.native
        def _isr(t):
            pos = self._buf_pos
            if pos < buf_len:
                pwm.duty_u16(buf[pos] * 257)
                self._buf_pos = pos + 1
            else:
                t.deinit()
                pwm.duty_u16(32768)
                self._playing = False

        timer.init(freq=self.sample_rate, mode=Timer.PERIODIC, callback=_isr)

        while self._playing:
            time.sleep_ms(10)

    def _play_loop(self, buffer):
        import time
        period_us = 1000000 // self.sample_rate
        pwm = self._pwm
        buf = buffer
        buf_len = len(buf)
        ticks_us = time.ticks_us
        ticks_diff = time.ticks_diff
        sleep_us = time.sleep_us

        next_t = ticks_us()
        for i in range(buf_len):
            pwm.duty_u16(buf[i] * 257)
            next_t += period_us
            wait = ticks_diff(next_t, ticks_us())
            if wait > 0:
                sleep_us(wait)

        pwm.duty_u16(32768)
        self._playing = False

    def stop(self):
        self._playing = False
        if self._timer:
            try:
                self._timer.deinit()
            except:
                pass
            self._timer = None
        if self._pwm:
            self._pwm.duty_u16(32768)
            try:
                self._pwm.deinit()
            except:
                pass
            self._pwm = None

    @property
    def is_playing(self):
        return self._playing


class WavWriter:
    def __init__(self, filename, sample_rate=SAMPLE_RATE):
        self.filename = filename
        self.sample_rate = sample_rate

    def write(self, buffer):
        import struct
        num_samples = len(buffer)
        with open(self.filename, 'wb') as f:
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + num_samples))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16))
            f.write(struct.pack('<H', 1))
            f.write(struct.pack('<H', 1))
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<H', 1))
            f.write(struct.pack('<H', 8))
            f.write(b'data')
            f.write(struct.pack('<I', num_samples))
            f.write(bytes(buffer))
        return self.filename
