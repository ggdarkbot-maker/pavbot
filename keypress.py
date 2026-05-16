import threading
import time
import pydirectinput

class KeyPressController:
    def __init__(self):
        self.stop_event = threading.Event()
        self.is_spamming = False
        self.spam_thread = None

    def _spam_loop(self, click_delay_ms, max_cycles=50):
        delay_sec = click_delay_ms / 1000.0
        cycles = 0
        while not self.stop_event.is_set() and cycles < max_cycles:
            pydirectinput.keyDown('e')
            pydirectinput.keyDown('enter')
            time.sleep(0.005)
            pydirectinput.keyUp('e')
            pydirectinput.keyUp('enter')
            time.sleep(delay_sec)
            cycles += 1

    def start_spam(self, click_delay_ms):
        if self.is_spamming:
            return
        self.stop_event.clear()
        self.is_spamming = True
        self.spam_thread = threading.Thread(target=self._spam_loop, args=(click_delay_ms,), daemon=True)
        self.spam_thread.start()

    def stop_spam(self):
        self.stop_event.set()
        self.is_spamming = False
        if self.spam_thread and self.spam_thread.is_alive():
            self.spam_thread.join(timeout=0.5)

    def is_running(self):
        return self.is_spamming