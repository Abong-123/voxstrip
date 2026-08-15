import whisper
import warnings
import numpy as np
from typing import List, Dict

# Suppress warnings
warnings.filterwarnings("ignore")

class AudioTranscriber:
    """Whisper-based audio transcription"""
    
    def __init__(self, model_name: str = "tiny"):
        """Initialize Whisper model"""
        print(f"📥 Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)
        print("✅ Model loaded!")
    
    def transcribe(self, audio_path: str, language: str = "en") -> Dict:
        """Transcribe audio file and return text with timestamps"""
        try:
            print(f"🎯 Transcribing: {audio_path}")
            
            # Transcribe with word timestamps
            result = self.model.transcribe(
                audio_path,
                language=language,
                word_timestamps=True,
                verbose=False,
                # Add these parameters for better accuracy
                temperature=0.0,  # More deterministic
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0,
                no_speech_threshold=0.6,
                condition_on_previous_text=True,
                initial_prompt="This is a song with explicit lyrics that need to be censored."
            )
            
            # Extract segments with words
            segments = []
            for segment in result["segments"]:
                for word in segment["words"]:
                    word_text = word["word"].strip().lower()
                    # Skip punctuation-only or very short words
                    if len(word_text) < 2:
                        continue
                    
                    segments.append({
                        "word": word_text,
                        "start": word["start"],
                        "end": word["end"],
                        "confidence": word.get("probability", 1.0)
                    })
            
            # Debug: print all detected words with confidence
            print("\n📝 Detected words:")
            for seg in segments:
                print(f"  '{seg['word']}' ({seg['start']:.2f}s - {seg['end']:.2f}s) conf: {seg['confidence']:.2f}")
            
            return {
                "text": result["text"],
                "segments": segments,
                "language": result.get("language", language)
            }
            
        except Exception as e:
            print(f"❌ Transcription error: {str(e)}")
            raise e

# Singleton instance
transcriber = None

def get_transcriber(model_name: str = "tiny"):
    """Get or create transcriber instance"""
    global transcriber
    if transcriber is None:
        transcriber = AudioTranscriber(model_name)
    return transcriber

def transcribe_audio(audio_path: str, language: str = "en") -> Dict:
    """Main function to transcribe audio"""
    global transcriber
    if transcriber is None:
        transcriber = AudioTranscriber("tiny")
    
    return transcriber.transcribe(audio_path, language)