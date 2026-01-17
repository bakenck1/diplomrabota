/**
 * Confirmation screen for transcript verification.
 * Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
 */

'use client';

import { useState } from 'react';
import { Check, Edit, RefreshCw } from 'lucide-react';

interface ConfirmationScreenProps {
  transcript: string;
  confidence: number;
  onConfirm: () => void;
  onCorrect: (correctedText: string) => void;
  onRetry: () => void;
}

export function ConfirmationScreen({
  transcript,
  confidence,
  onConfirm,
  onCorrect,
  onRetry,
}: ConfirmationScreenProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(transcript);

  const handleCorrectSubmit = () => {
    if (editedText.trim() && editedText !== transcript) {
      onCorrect(editedText.trim());
    }
    setIsEditing(false);
  };

  const confidenceColor = confidence >= 0.8 
    ? 'text-green-600' 
    : confidence >= 0.6 
      ? 'text-yellow-600' 
      : 'text-red-600';

  return (
    <div className="w-full max-w-2xl mx-auto p-6 space-y-6">
      {/* Transcript display */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <p className="text-gray-500 text-senior mb-2">Вы сказали:</p>
        
        {isEditing ? (
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className="w-full p-4 text-senior-xl border-2 border-blue-300 rounded-lg focus:border-blue-500 focus:outline-none min-h-[120px]"
            autoFocus
          />
        ) : (
          <p className="text-senior-2xl font-medium text-gray-900 leading-relaxed">
            "{transcript}"
          </p>
        )}

        {/* Confidence indicator */}
        <div className="mt-4 flex items-center gap-2">
          <span className="text-gray-500">Уверенность:</span>
          <span className={`font-semibold ${confidenceColor}`}>
            {Math.round(confidence * 100)}%
          </span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-1 gap-4">
        {isEditing ? (
          <>
            <button
              onClick={handleCorrectSubmit}
              className="w-full py-5 px-6 bg-green-500 text-white rounded-xl text-senior-lg font-semibold flex items-center justify-center gap-3 hover:bg-green-600 transition-colors"
            >
              <Check className="w-8 h-8" />
              Сохранить исправление
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                setEditedText(transcript);
              }}
              className="w-full py-5 px-6 bg-gray-200 text-gray-700 rounded-xl text-senior-lg font-semibold hover:bg-gray-300 transition-colors"
            >
              Отмена
            </button>
          </>
        ) : (
          <>
            <button
              onClick={onConfirm}
              className="w-full py-5 px-6 bg-green-500 text-white rounded-xl text-senior-lg font-semibold flex items-center justify-center gap-3 hover:bg-green-600 transition-colors"
            >
              <Check className="w-8 h-8" />
              Да, верно
            </button>
            
            <button
              onClick={() => setIsEditing(true)}
              className="w-full py-5 px-6 bg-yellow-500 text-white rounded-xl text-senior-lg font-semibold flex items-center justify-center gap-3 hover:bg-yellow-600 transition-colors"
            >
              <Edit className="w-8 h-8" />
              Исправить
            </button>
            
            <button
              onClick={onRetry}
              className="w-full py-5 px-6 bg-blue-500 text-white rounded-xl text-senior-lg font-semibold flex items-center justify-center gap-3 hover:bg-blue-600 transition-colors"
            >
              <RefreshCw className="w-8 h-8" />
              Повторить
            </button>
          </>
        )}
      </div>
    </div>
  );
}
