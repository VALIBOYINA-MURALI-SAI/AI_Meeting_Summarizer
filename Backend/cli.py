import os
import re
import sys
import time
import threading
import subprocess
import torch
import whisper
import ffmpeg
import queue
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
from dotenv import load_dotenv
from offline_summarizer import summarize_text_offline
from meeting_summarizer import MeetingProcessor

try:
    processor = MeetingProcessor()
except Exception as e:
    print(f"❌ Failed to initialize MeetingProcessor: {e}")
    sys.exit(1)


print("\U0001f50d [INFO] Loading .env file...")
loaded = load_dotenv()
print(f"✅ [INFO] .env loaded: {loaded}")

whisper_model = "base"
stop_ticker = True

def display_ticker():
    start_time = time.time()
    while not stop_ticker:
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(int(elapsed_time), 60)
        sys.stdout.write(f'\r🎙️ [INFO] Recording: {minutes:02d}:{seconds:02d}')
        sys.stdout.flush()
        time.sleep(1)

def record_meeting(output_filename):
    global stop_ticker
    stop_ticker = False
    ticker_thread = threading.Thread(target=display_ticker)
    ticker_thread.start()

    fs = 44100  # Sample rate
    channels = 1
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"⚠️ [WARNING] {status}", file=sys.stderr)
        q.put(indata.copy())

    try:
        print("\n🎥 [INFO] Recording started. Press Ctrl+C to stop.")
        with sd.InputStream(samplerate=fs, channels=channels, callback=callback):
            recorded_frames = []
            while True:
                try:
                    frame = q.get(timeout=1)
                    recorded_frames.append(frame)
                except queue.Empty:
                    continue
    except KeyboardInterrupt:
        print("\n🛑 [INFO] Recording manually stopped.")
    except Exception as e:
        print(f"❌ [ERROR] Recording error: {e}")
    finally:
        stop_ticker = True
        ticker_thread.join()

        if recorded_frames:
            audio_data = np.concatenate(recorded_frames, axis=0)
            write(output_filename, fs, audio_data)
            print(f"✅ [INFO] Recording saved to {output_filename}")
        else:
            print("⚠️ [WARNING] No audio recorded.")

def transcribe_audio(filename):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = whisper.load_model(whisper_model, device=device)
    audio = whisper.load_audio(filename)

    print("📝 [INFO] Beginning transcription...")
    result = model.transcribe(audio, verbose=False, fp16=False, task="translate")
    return result['text']

def summarize_transcript(transcript):
    return summarize_text_offline(transcript)

def action_items(transcript):
    items = processor.extract_action_items(transcript)  # Use the processor instance
    
    # Post-processing to improve quality
    if len(items) == 1 and not items[0].startswith("•"):
        return items
    
    # Remove duplicates and empty items
    seen = set()
    unique_items = []
    for item in items:
        norm_item = re.sub(r'[^a-zA-Z0-9]', '', item.lower())
        if norm_item and norm_item not in seen:
            seen.add(norm_item)
            unique_items.append(item)
    
    return unique_items[:10]

def save_results_to_file(transcript, summary, action_items, output_path="meeting_summary.txt"):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("🔊 TRANSCRIPT:\n")
        f.write(transcript + "\n\n")

        f.write("📝 SUMMARY_START:\n")
        f.write(summary + "\n")
        f.write("📝 SUMMARY_END\n\n")

        f.write("✅ ACTION_ITEMS_START:\n")
        for item in action_items:
            f.write(f"- {item}\n")
        f.write("✅ ACTION_ITEMS_END\n")

    print(f"\n💾 [INFO] Results saved to {output_path}")


# At the bottom of cli.py, change the if __name__ block to:
def main():
    if len(sys.argv) != 3:
        print(f"⚠️ [USAGE] python {sys.argv[0]} [record|summarize] output.wav")
        sys.exit(1)

    action = sys.argv[1]
    output_filename = sys.argv[2]

    if action == "record":
        record_meeting(output_filename)

    elif action == "summarize":
        try:
            print("🔍 Starting processing...")
            transcript = transcribe_audio(output_filename)
            print("\n=== TRANSCRIPT ===\n")
            print(transcript[:] + "...\n")  # Print first 1000 chars to avoid flooding console
            summary = summarize_transcript(transcript)
            print("\n=== SUMMARY ===\nSUMMARY_START")
            print(summary)
            print("SUMMARY_END")
            items = action_items(transcript)  # Use the unified function

            print("\n=== ACTION ITEMS ===\nACTION_ITEMS_START")
            if len(items) == 1 and not items[0].startswith("•"):
                print(items[0])
            else:
                for idx, item in enumerate(items, 1):
                    print(f"{idx}. {item}")
            print("ACTION_ITEMS_END")
    
            save_results_to_file(transcript, summary, items)
    
        except Exception as e:
            print(f"❌ Processing failed: {e}") 
        
    elif action == "transcribe":
        print("[INFO] Transcribing only...")
        transcript = transcribe_audio(output_filename)
        with open("transcript.txt", "w", encoding="utf-8") as f:
            f.write(transcript)
        print("[INFO] Transcription complete and saved to transcript.txt")
    else:
        print(f"⚠️ [ERROR] Invalid action. Usage: python {sys.argv[0]} [record|summarize] output.wav")
        sys.exit(1)

if __name__ == "__main__":
    main()