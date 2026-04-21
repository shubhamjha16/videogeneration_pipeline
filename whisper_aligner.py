"""
Whisper Aligner — High-Fidelity Subtitle Alignment
Powered by faster-whisper.

Transcribes audio and extracts word-level timestamps for perfectly synced subtitles.
Optimized for 24GB RAM Mac Mini using the 'small.en' model.
"""

import os
import time
from typing import List, Dict, Any
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

# Model Configuration
MODEL_SIZE = "small.en"  # High accuracy for technical/mathematical curricula
COMPUTE_TYPE = "int8"   # Optimized for CPU usage on 24GB Intel Mac

# Global Model Singleton (Lazy Loaded)
_model_instance = None

def _get_model():
    """Industrial Singleton: Loads the Whisper model into RAM only when needed."""
    global _model_instance
    if _model_instance is None:
        if WhisperModel is None:
            print("❌ faster-whisper not installed. Alignment disabled.")
            return None
        
        print(f"🎬 [Whisper Aligner] Loading '{MODEL_SIZE}' model (Compute: {COMPUTE_TYPE})...")
        start_time = time.time()
        # cpu_threads=4 to avoid thrashing the Gemma LLM process
        _model_instance = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE, cpu_threads=4)
        print(f"✅ Model loaded in {time.time() - start_time:.2f}s")
        
    return _model_instance

def get_word_timestamps(audio_path: str) -> List[Dict[str, Any]]:
    """
    Transcribes the provided audio and returns a list of word-level timestamps.
    
    Returns:
        List[Dict]: [{"word": "Text", "start": 0.0, "end": 0.5}, ...]
    """
    model = _get_model()
    if not model or not os.path.exists(audio_path):
        return []

    print(f"🔎 [Whisper Aligner] Aligning audio: {os.path.basename(audio_path)}...")
    
    # transcribe with word_timestamps=True for frame-perfect alignment
    # task="transcribe" ensures we don't accidentally translate non-English narrations
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    
    all_words = []
    for segment in segments:
        if segment.words:
            for word in segment.words:
                all_words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                })
    
    print(f"✅ [Whisper Aligner] Extracted {len(all_words)} words.")
    return all_words

if __name__ == "__main__":
    # Standalone Test
    import sys
    if len(sys.argv) > 1:
        test_audio = sys.argv[1]
        results = get_word_timestamps(test_audio)
        for r in results[:10]: # Print first 10
            print(f"[{r['start']:.2f}s -> {r['end']:.2f}s] {r['word']}")
    else:
        print("Usage: python3 whisper_aligner.py <path_to_audio_mp3>")
