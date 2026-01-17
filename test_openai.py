import asyncio
import io
from src.config import get_settings
from openai import AsyncOpenAI

async def test():
    settings = get_settings()
    print(f"Using API key: {settings.openai_api_key[:20]}...")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # Create a simple test audio
    import wave
    import struct
    import math
    
    sample_rate = 16000
    duration = 2
    samples = [int(32767 * 0.5 * math.sin(2 * math.pi * 440 * t / sample_rate)) for t in range(sample_rate * duration)]
    
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
    
    buffer.seek(0)
    buffer.name = 'test.wav'
    
    try:
        response = await client.audio.transcriptions.create(
            model='whisper-1',
            file=buffer,
            language='ru',
        )
        print(f'Success: "{response.text}"')
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')

asyncio.run(test())
