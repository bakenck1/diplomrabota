/**
 * Main Senior UI page for voice assistant.
 * Validates: Requirements 1.1, 1.2, 1.5, 2.1-2.6
 */

'use client';

import { useState, useCallback } from 'react';
import { VoiceButton } from '@/components/VoiceButton';
import { ConfirmationScreen } from '@/components/ConfirmationScreen';
import { ResponsePlayer } from '@/components/ResponsePlayer';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { voiceApi, TranscribeResponse, RespondResponse } from '@/services/api';

type AppState = 'idle' | 'recording' | 'processing' | 'confirming' | 'responding' | 'playing';

export default function Home() {
  const [state, setState] = useState<AppState>('idle');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcription, setTranscription] = useState<TranscribeResponse | null>(null);
  const [response, setResponse] = useState<RespondResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { isRecording, startRecording, stopRecording } = useAudioRecorder();

  // Initialize session
  const initSession = useCallback(async () => {
    if (!sessionId) {
      try {
        const { session_id } = await voiceApi.createSession({
          userAgent: navigator.userAgent,
        });
        setSessionId(session_id);
        return session_id;
      } catch (err) {
        setError('Не удалось создать сессию');
        return null;
      }
    }
    return sessionId;
  }, [sessionId]);

  // Start recording
  const handlePressStart = useCallback(async () => {
    setError(null);
    await startRecording();
    setState('recording');
  }, [startRecording]);

  // Stop recording and process
  const handlePressEnd = useCallback(async () => {
    setState('processing');
    
    try {
      const audioBlob = await stopRecording();
      const currentSessionId = await initSession();
      
      if (!currentSessionId) {
        setState('idle');
        return;
      }

      const result = await voiceApi.uploadAudio(currentSessionId, audioBlob);
      setTranscription(result);
      setState('confirming');
    } catch (err) {
      setError('Ошибка при обработке аудио');
      setState('idle');
    }
  }, [stopRecording, initSession]);

  // Confirm transcript
  const handleConfirm = useCallback(async () => {
    if (!sessionId || !transcription) return;

    setState('responding');
    
    try {
      await voiceApi.confirmTranscript(sessionId, transcription.turn_id, true);
      
      // Generate response (in real app, this would come from LLM)
      const assistantText = `Я понял вас: "${transcription.normalized_transcript}". Чем могу помочь?`;
      const result = await voiceApi.generateResponse(
        sessionId,
        transcription.turn_id,
        assistantText
      );
      
      setResponse(result);
      setState('playing');
    } catch (err) {
      setError('Ошибка при генерации ответа');
      setState('idle');
    }
  }, [sessionId, transcription]);

  // Correct transcript
  const handleCorrect = useCallback(async (correctedText: string) => {
    if (!sessionId || !transcription) return;

    setState('responding');
    
    try {
      await voiceApi.confirmTranscript(sessionId, transcription.turn_id, false, correctedText);
      
      const assistantText = `Спасибо за исправление. Вы сказали: "${correctedText}". Чем могу помочь?`;
      const result = await voiceApi.generateResponse(
        sessionId,
        transcription.turn_id,
        assistantText
      );
      
      setResponse(result);
      setState('playing');
    } catch (err) {
      setError('Ошибка при сохранении исправления');
      setState('idle');
    }
  }, [sessionId, transcription]);

  // Retry recording
  const handleRetry = useCallback(() => {
    setTranscription(null);
    setState('idle');
  }, []);

  // Response playback complete
  const handlePlaybackComplete = useCallback(() => {
    setState('idle');
    setTranscription(null);
    setResponse(null);
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <h1 className="text-senior-2xl font-bold text-center text-gray-800 mb-8">
          Голосовой помощник
        </h1>

        {/* Error display */}
        {error && (
          <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-xl text-senior text-center">
            {error}
          </div>
        )}

        {/* Main content based on state */}
        {(state === 'idle' || state === 'recording' || state === 'processing') && (
          <div className="flex flex-col items-center gap-6">
            <p className="text-senior-lg text-gray-600 text-center">
              {state === 'recording' 
                ? 'Говорите...' 
                : state === 'processing'
                  ? 'Обрабатываю...'
                  : 'Нажмите и удерживайте кнопку, чтобы говорить'
              }
            </p>
            
            <VoiceButton
              isRecording={isRecording}
              isProcessing={state === 'processing'}
              onPressStart={handlePressStart}
              onPressEnd={handlePressEnd}
            />
          </div>
        )}

        {state === 'confirming' && transcription && (
          <ConfirmationScreen
            transcript={transcription.normalized_transcript}
            confidence={transcription.confidence}
            onConfirm={handleConfirm}
            onCorrect={handleCorrect}
            onRetry={handleRetry}
          />
        )}

        {state === 'responding' && (
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-senior-lg text-gray-600">Генерирую ответ...</p>
          </div>
        )}

        {state === 'playing' && response && (
          <ResponsePlayer
            text={response.assistant_text}
            audioUrl={response.audio_url}
            onComplete={handlePlaybackComplete}
          />
        )}
      </div>
    </main>
  );
}
