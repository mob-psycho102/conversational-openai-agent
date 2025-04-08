import sys
import pandas as pd
import queue
import sounddevice as sd
import vosk
import json
import asyncio
import threading
from openai import AsyncOpenAI
from openai import OpenAI
from openai.helpers import LocalAudioPlayer
from PySide6.QtCore import Qt, QThreadPool, QRunnable, Signal, Slot, QObject
from PySide6.QtWidgets import QApplication

# Import the Siri-like bubble interface
from siri_bubble import SiriBubbleWindow

# Load environment variables
from dotenv import load_dotenv
import os
load_dotenv()

# Global variables
chosen_word = None
conversation_history = []

# Setup OpenAI clients
openai = AsyncOpenAI()
client = OpenAI()

# Voice instructions for text-to-speech
instructions = """Delivery: Exaggerated and theatrical, with dramatic pauses, sudden outbursts, and gleeful cackling.
Voice: High-energy, eccentric, and slightly unhinged, with a manic enthusiasm that rises and falls unpredictably.
Tone: Excited, chaotic, and grandiose, as if reveling in the brilliance of a mad experiment.
Pronunciation: Sharp and expressive, with elongated vowels, sudden inflections, and an emphasis on big words to sound more diabolical."""

# Load words list
try:
    words_list_df = pd.read_csv('words_list.csv')
except Exception as e:
    print(f"Error loading words list: {e}")
    # Create a sample word list if file not found
    words_list_df = pd.DataFrame({
        'word': ['serendipity', 'ephemeral', 'ubiquitous', 'esoteric', 'pragmatic', 
                'eloquent', 'paradox', 'ambiguous', 'meticulous', 'resilient']
    })

# Setup audio parameters
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000
MODEL_PATH = "vosk-model-small-en-us-0.15"  # Adjust path as needed

# Initialize Vosk model
try:
    model = vosk.Model(MODEL_PATH)
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
except Exception as e:
    print(f"Error loading Vosk model: {e}")
    print("Please download the Vosk model from https://alphacephei.com/vosk/models")
    print("and place it in the correct directory")
    sys.exit(1)

q = queue.Queue()

# Worker signal class for threading
class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)
    result = Signal(object)
    progress = Signal(int)
    status_update = Signal(str)

# Audio callback function
def audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status, file=sys.stderr)
    q.put(bytes(indata))

# Worker class for speech recognition
class SpeechRecognitionWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.is_running = True
    
    @Slot()
    def run(self):
        user_input_string = ""
        
        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                                dtype='int16', channels=1, callback=audio_callback):
                
                # Signal that we're ready to listen
                self.signals.status_update.emit("LISTENING")
                
                while self.is_running:
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        print("CURRENT TEXT IS : ",text.strip())
                        if "up to you" in text.strip() or "upto you" in text.strip() or "your turn" in text.strip() or "next to you" in text.strip() or "over to you" in text.strip() :
                            print('$$$$ got it you are saying', text.strip())
                            self.signals.result.emit(user_input_string)
                            break
                        
                        if "give me a new word" in text.strip() or "new word" in text.strip()  or "another word" in text.strip():
                            print("Detected: change word please")
                            self.signals.status_update.emit("CHANGE_WORD")
                            user_input_string = "change word please"
                            self.signals.result.emit(user_input_string)
                            break
                            
                        if "goodbye" in text.strip() or "good bye" in text.strip():
                            print("Detected: close this conversation please")
                            self.signals.status_update.emit("CLOSE")
                            user_input_string = "close this conversation please"
                            self.signals.result.emit(user_input_string)
                            break
                        
                        if text.strip():
                            user_input_string += text + " "
                            print("You said:", text)
                            # Update status
                            self.signals.progress.emit(len(user_input_string))
                        
                    else:
                        partial = json.loads(rec.PartialResult())
                        print("...", partial.get("partial", ""), end="\r")
        
        except Exception as e:
            print(f"Speech recognition error: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
    
    def stop(self):
        self.is_running = False

# Worker for GPT-4o processing
class GPT4oWorker(QRunnable):
    def __init__(self, user_input):
        super().__init__()
        self.signals = WorkerSignals()
        self.user_input = user_input
    
    @Slot()
    def run(self):
        try:
            response = self.ask_gpt4o(self.user_input)
            self.signals.result.emit(response)
        except Exception as e:
            print(f"GPT-4o error: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
    
    def ask_gpt4o(self, user_input):
        global conversation_history
        
        try:
            # Add the user's input to the conversation history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Make the request to GPT-4o with the full conversation context
            response = client.responses.create(
                model="gpt-4o",
                input=conversation_history  # Pass all previous messages for context
            )

            # Extract the assistant's reply
            reply = response.output_text.strip()

            # Add the assistant's response to the conversation history
            conversation_history.append({"role": "assistant", "content": reply})

            return reply

        except Exception as e:
            return f"Error from GPT-4o: {e}"

# TTS Worker
class TTSWorker(QRunnable):
    def __init__(self, text):
        super().__init__()
        self.signals = WorkerSignals()
        self.text = text
    
    @Slot()
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.get_text_to_speech(self.text))
            self.signals.result.emit("TTS_COMPLETE")
        except Exception as e:
            print(f"TTS error: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
    
    async def get_text_to_speech(self, inp_text):
        try:
            async with openai.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=inp_text,
                instructions=instructions,
                response_format="pcm",
            ) as response:
                await LocalAudioPlayer().play(response)
        except Exception as e:
            print(f"Error in TTS streaming: {e}")
            raise

# Main application class
class VocabularyApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.bubble_window = SiriBubbleWindow()
        self.thread_pool = QThreadPool()
        
        # Set maximum thread count
        self.thread_pool.setMaxThreadCount(5)
        
        # Current state
        self.listening = False
        self.processing = False
        self.speaking = False
        
        # Initialize speech recognition worker
        self.speech_worker = None
        
    def start(self):
        print("Starting vocabulary practice application...")
        self.bubble_window.show()
        self.select_new_word()
        return self.app.exec()
        
    def select_new_word(self):
        global chosen_word
        global conversation_history
        
        print("Selecting a new word...")
        
        # Reset UI
        self.bubble_window.reset()
        
        # Select a new word
        chosen_word = words_list_df.sample(n=1).iloc[0]["word"]
        print(f"Selected word: {chosen_word}")
        
        # Reset conversation history for new word
        conversation_history = [
            {"role": "system", "content": "You are a helpful, friendly AI assistant."},
            {"role": "user", "content": "I want to practice some word meanings of English language which people use in their day to day life"},
            {"role": "assistant", "content": f"Great! You can start with {chosen_word}. Explain the meaning of this word if you know, otherwise I will tell you."}
        ]
        
        # Display the word and prepare TTS prompt
        self.bubble_window.set_word(f"Explain: {chosen_word}")
        
        # Start TTS for the prompt
        tts_worker = TTSWorker(f'Explain the meaning of {chosen_word}')
        tts_worker.signals.finished.connect(self.on_tts_finished)
        tts_worker.signals.error.connect(self.on_error)
        self.bubble_window.start_speaking()
        self.thread_pool.start(tts_worker)
    
    def on_tts_finished(self):
        print("TTS finished, starting listening...")
        # Start listening for user input
        self.start_listening()
    
    def start_listening(self):
        # Update UI
        self.bubble_window.start_listening()
        
        # Start speech recognition worker
        self.speech_worker = SpeechRecognitionWorker()
        self.speech_worker.signals.result.connect(self.on_speech_result)
        self.speech_worker.signals.error.connect(self.on_error)
        self.speech_worker.signals.status_update.connect(self.on_status_update)
        self.thread_pool.start(self.speech_worker)
    
    def on_speech_result(self, user_input):
        print(f"Received speech result: {user_input[:50]}...")
        
        if user_input == "change word please":
            print("Changing word...")
            self.select_new_word()
            return
        
        if user_input == "close this conversation please":
            print("Closing application...")
            self.app.quit()
            return
        
        # Process with GPT-4o
        self.bubble_window.start_processing()
        
        gpt_worker = GPT4oWorker(user_input)
        gpt_worker.signals.result.connect(self.on_gpt_result)
        gpt_worker.signals.error.connect(self.on_error)
        self.thread_pool.start(gpt_worker)
    
    def on_gpt_result(self, response):
        print(f"Received GPT response: {response[:50]}...")
        # Speak the response
        self.bubble_window.start_speaking(f"Responding: {chosen_word}")
        
        tts_worker = TTSWorker(response)
        tts_worker.signals.finished.connect(self.after_response)
        tts_worker.signals.error.connect(self.on_error)
        self.thread_pool.start(tts_worker)
    
    def after_response(self):
        print("Response complete, listening for next input...")
        # After speaking the response, go back to listening
        self.start_listening()
    
    def on_status_update(self, status):
        print(f"Status update: {status}")
        
    def on_error(self, error_msg):
        print(f"Error: {error_msg}")
        # Handle error and recover
        self.bubble_window.reset()
        self.bubble_window.set_word(f"Error: {error_msg[:20]}...")
        
        # Try to recover after a short delay
        QTimer.singleShot(3000, self.select_new_word)

if __name__ == "__main__":
    app = VocabularyApp()
    sys.exit(app.start())