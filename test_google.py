import asyncio
import io
import wave
import struct
import math
from src.config import get_settings

async def test():
    settings = get_settings()
    print(f"Using Google API key: {settings.google_api_key[:20]}...")
    
    import google.generativeai as genai
    import base64
    
    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Create test audio
    sample_rate = 16000
    duration = 2
    samples = [int(32767 * 0.5 * math.sin(2 * math.pi * 440 * t / sample_rate)) for t in range(sample_rate * duration)]
    
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
    
    audio_bytes = buffer.getvalue()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    try:
        response = model.generate_content([
            "Распознай речь на русском языке из этого аудио. Верни только распознанный текст.",
            {
                "mime_type": "audio/wav",
                "data": audio_b64
            }
        ])
        print(f'Success: "{response.text}"')
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')

asyncio.run(test())
