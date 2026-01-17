/**
 * Audio player for TTS response with text display.
 * Validates: Requirements 1.5
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2 } from 'lucide-react';

interface ResponsePlayerProps {
  text: string;
  audioUrl: string;
  onComplete?: () => void;
}

export function ResponsePlayer({ text, audioUrl, onComplete }: ResponsePlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);
  
  // Build full audio URL (backend is on different port)
  const fullAudioUrl = audioUrl.startsWith('http') 
    ? audioUrl 
    : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${audioUrl}`;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      if (audio.duration) {
        setProgress((audio.currentTime / audio.duration) * 100);
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
      onComplete?.();
    };

    const handleError = (e: Event) => {
      console.error('Audio playback error:', e);
      setIsPlaying(false);
    };

    const handleCanPlay = () => {
      // Auto-play when audio is ready
      audio.play().then(() => setIsPlaying(true)).catch(console.error);
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
    audio.addEventListener('canplay', handleCanPlay);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('canplay', handleCanPlay);
    };
  }, [audioUrl, onComplete]);

  const togglePlayback = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 space-y-6">
      {/* Response text */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center gap-2 text-gray-500 mb-4">
          <Volume2 className="w-6 h-6" />
          <span className="text-senior">Ответ:</span>
        </div>
        
        <p className="text-senior-xl font-medium text-gray-900 leading-relaxed">
          {text}
        </p>
      </div>

      {/* Audio player */}
      <div className="bg-gray-100 rounded-xl p-4">
        <audio ref={audioRef} src={fullAudioUrl} preload="auto" />
        
        <div className="flex items-center gap-4">
          <button
            onClick={togglePlayback}
            className="w-16 h-16 bg-blue-500 text-white rounded-full flex items-center justify-center hover:bg-blue-600 transition-colors"
            aria-label={isPlaying ? 'Пауза' : 'Воспроизвести'}
          >
            {isPlaying ? (
              <Pause className="w-8 h-8" />
            ) : (
              <Play className="w-8 h-8 ml-1" />
            )}
          </button>

          {/* Progress bar */}
          <div className="flex-1 h-3 bg-gray-300 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-100"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
