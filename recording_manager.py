# recording_manager.py

import threading
import queue
import sys
import time
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

class RecordingManager:
    def __init__(self, output_filename="output.wav"):
        self.fs = 44100
        self.channels = 1
        self.q = queue.Queue()
        self.recorded_frames = []
        self.output_filename = output_filename
        self.is_recording = False
        self._ticker_thread = None
        self._record_thread = None

    def _display_ticker(self):
        start_time = time.time()
        while self.is_recording:
            elapsed_time = time.time() - start_time
            minutes, seconds = divmod(int(elapsed_time), 60)
            sys.stdout.write(f'\r🎙️ [INFO] Recording: {minutes:02d}:{seconds:02d}')
            sys.stdout.flush()
            time.sleep(1)

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"⚠️ [WARNING] {status}", file=sys.stderr)
        self.q.put(indata.copy())

    def _record(self):
        with sd.InputStream(samplerate=self.fs, channels=self.channels, callback=self._callback):
            while self.is_recording:
                try:
                    frame = self.q.get(timeout=1)
                    self.recorded_frames.append(frame)
                except queue.Empty:
                    continue

    def start_recording(self):
        print("🔴 [INFO] Starting recording...")
        self.recorded_frames = []
        self.is_recording = True
        self._ticker_thread = threading.Thread(target=self._display_ticker)
        self._record_thread = threading.Thread(target=self._record)
        self._ticker_thread.start()
        self._record_thread.start()

    def stop_recording(self):
        print("\n🛑 [INFO] Stopping recording...")
        self.is_recording = False
        self._record_thread.join()
        self._ticker_thread.join()

        if self.recorded_frames:
            audio_data = np.concatenate(self.recorded_frames, axis=0)
            write(self.output_filename, self.fs, audio_data)
            print(f"✅ [INFO] Recording saved to {self.output_filename}")
        else:
            print("⚠️ [WARNING] No audio recorded.")
