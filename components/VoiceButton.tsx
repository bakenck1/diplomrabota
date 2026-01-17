/**
 * Large voice recording button for senior users.
 * Validates: Requirements 1.1, 1.2
 */

'use client';

import { Mic, MicOff, Loader2 } from 'lucide-react';

interface VoiceButtonProps {
  isRecording: boolean;
  isProcessing: boolean;
  onPressStart: () => void;
  onPressEnd: () => void;
  disabled?: boolean;
}

export function VoiceButton({
  isRecording,
  isProcessing,
  onPressStart,
  onPressEnd,
  disabled = false,
}: VoiceButtonProps) {
  const handleMouseDown = () => {
    if (!disabled && !isProcessing) {
      onPressStart();
    }
  };

  const handleMouseUp = () => {
    if (isRecording) {
      onPressEnd();
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    e.preventDefault();
    handleMouseDown();
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    e.preventDefault();
    handleMouseUp();
  };

  return (
    <button
      className={`
        w-full max-w-md h-32 rounded-2xl
        flex items-center justify-center gap-4
        text-senior-xl font-semibold
        transition-all duration-200
        select-none touch-none
        ${isRecording 
          ? 'bg-red-500 text-white scale-105 shadow-lg' 
          : isProcessing
            ? 'bg-gray-400 text-white cursor-wait'
            : 'bg-blue-500 text-white hover:bg-blue-600 active:scale-95'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      disabled={disabled || isProcessing}
      aria-label={isRecording ? 'Отпустите чтобы остановить' : 'Нажмите и говорите'}
    >
      {isProcessing ? (
        <>
          <Loader2 className="w-10 h-10 animate-spin" />
          <span>Обработка...</span>
        </>
      ) : isRecording ? (
        <>
          <MicOff className="w-10 h-10" />
          <span>Отпустите</span>
        </>
      ) : (
        <>
          <Mic className="w-10 h-10" />
          <span>Говорить</span>
        </>
      )}
    </button>
  );
}
