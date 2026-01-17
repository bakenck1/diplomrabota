'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { adminApi, ConversationDetails } from '@/services/api';

export default function ConversationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [conversation, setConversation] = useState<ConversationDetails | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConversation();
  }, [params.id]);

  const loadConversation = async () => {
    try {
      const data = await adminApi.getConversation(params.id as string);
      setConversation(data);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Загрузка...</div>;
  }

  if (!conversation) {
    return <div className="text-center py-8 text-red-600">Диалог не найден</div>;
  }

  return (
    <div>
      <button
        onClick={() => router.back()}
        className="text-blue-600 hover:text-blue-800 mb-4 text-sm"
      >
        ← Назад к списку
      </button>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">Диалог</h1>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Начало:</span>
            <p className="font-medium">{new Date(conversation.started_at).toLocaleString()}</p>
          </div>
          <div>
            <span className="text-gray-500">Окончание:</span>
            <p className="font-medium">
              {conversation.ended_at ? new Date(conversation.ended_at).toLocaleString() : '—'}
            </p>
          </div>
          <div>
            <span className="text-gray-500">STT провайдер:</span>
            <p className="font-medium">{conversation.stt_provider_used}</p>
          </div>
          <div>
            <span className="text-gray-500">TTS провайдер:</span>
            <p className="font-medium">{conversation.tts_provider_used}</p>
          </div>
        </div>
      </div>

      <h2 className="text-xl font-bold text-gray-800 mb-4">Шаги диалога</h2>

      <div className="space-y-4">
        {conversation.turns.map((turn) => (
          <div key={turn.id} className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start mb-4">
              <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                Шаг {turn.turn_number}
              </span>
              <span className="text-sm text-gray-500">
                {new Date(turn.timestamp).toLocaleTimeString()}
              </span>
            </div>

            {/* User input */}
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Пользователь сказал:</h3>
              {turn.audio_input_url && (
                <audio controls className="w-full mb-2" src={turn.audio_input_url}>
                  Ваш браузер не поддерживает аудио
                </audio>
              )}
              <div className="bg-gray-50 rounded p-3">
                <p className="text-gray-600 text-sm mb-1">
                  <span className="font-medium">Raw:</span> {turn.raw_transcript || '—'}
                </p>
                <p className="text-gray-800">
                  <span className="font-medium text-sm text-gray-600">Normalized:</span>{' '}
                  {turn.normalized_transcript || '—'}
                </p>
              </div>
              {turn.user_correction && (
                <p className="text-orange-600 text-sm mt-2">
                  ✏️ Исправлено пользователем: {turn.user_correction}
                </p>
              )}
            </div>

            {/* Metrics */}
            <div className="flex gap-4 mb-4 text-sm">
              <div className="bg-gray-100 rounded px-3 py-1">
                <span className="text-gray-500">Confidence:</span>{' '}
                <span
                  className={
                    (turn.transcript_confidence || 0) < 0.7 ? 'text-red-600' : 'text-green-600'
                  }
                >
                  {((turn.transcript_confidence || 0) * 100).toFixed(1)}%
                </span>
              </div>
              {turn.stt_latency_ms && (
                <div className="bg-gray-100 rounded px-3 py-1">
                  <span className="text-gray-500">STT:</span> {turn.stt_latency_ms}ms
                </div>
              )}
              {turn.tts_latency_ms && (
                <div className="bg-gray-100 rounded px-3 py-1">
                  <span className="text-gray-500">TTS:</span> {turn.tts_latency_ms}ms
                </div>
              )}
            </div>

            {/* Assistant response */}
            {turn.assistant_text && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Ответ ассистента:</h3>
                {turn.audio_output_url && (
                  <audio controls className="w-full mb-2" src={turn.audio_output_url}>
                    Ваш браузер не поддерживает аудио
                  </audio>
                )}
                <div className="bg-blue-50 rounded p-3">
                  <p className="text-gray-800">{turn.assistant_text}</p>
                </div>
              </div>
            )}
          </div>
        ))}

        {conversation.turns.length === 0 && (
          <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
            Нет шагов в диалоге
          </div>
        )}
      </div>
    </div>
  );
}
