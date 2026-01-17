/**
 * API client for Voice Assistant backend.
 */

import axios from 'axios';

const API_URL = process.env.API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Types
export interface SessionResponse {
  session_id: string;
}

export interface TranscribeResponse {
  turn_id: string;
  raw_transcript: string;
  normalized_transcript: string;
  confidence: number;
  stt_latency_ms: number;
}

export interface RespondResponse {
  assistant_text: string;
  audio_url: string;
  tts_latency_ms: number;
}

export interface ConfirmResponse {
  success: boolean;
}

// Voice API
export const voiceApi = {
  createSession: async (deviceInfo?: object): Promise<SessionResponse> => {
    const response = await api.post('/api/voice/session', { device_info: deviceInfo });
    return response.data;
  },

  uploadAudio: async (sessionId: string, audioBlob: Blob): Promise<TranscribeResponse> => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    
    const response = await api.post(`/api/voice/upload/${sessionId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  confirmTranscript: async (
    sessionId: string,
    turnId: string,
    confirmed: boolean,
    correction?: string
  ): Promise<ConfirmResponse> => {
    const response = await api.post(`/api/voice/confirm/${sessionId}`, {
      turn_id: turnId,
      confirmed,
      correction,
    });
    return response.data;
  },

  generateResponse: async (
    sessionId: string,
    turnId: string,
    assistantText: string
  ): Promise<RespondResponse> => {
    const response = await api.post(`/api/voice/respond/${sessionId}`, {
      turn_id: turnId,
      assistant_text: assistantText,
    });
    return response.data;
  },

  endSession: async (sessionId: string): Promise<void> => {
    await api.post(`/api/voice/end/${sessionId}`);
  },
};

// Auth API
export const authApi = {
  login: async (email: string, password: string): Promise<{ access_token: string }> => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await api.post('/api/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  getMe: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },
};

// Admin Types
export interface User {
  id: string;
  name: string;
  role: 'senior' | 'admin';
  language: 'ru' | 'kk';
  stt_provider: 'openai' | 'google';
  tts_provider: 'openai' | 'google';
  is_test_user: boolean;
  created_at: string;
  last_active_at?: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  user_name?: string;
  started_at: string;
  ended_at?: string;
  stt_provider_used: string;
  tts_provider_used: string;
  turn_count: number;
}

export interface Turn {
  id: string;
  turn_number: number;
  timestamp: string;
  audio_input_url?: string;
  raw_transcript?: string;
  normalized_transcript?: string;
  transcript_confidence?: number;
  user_confirmed?: boolean;
  user_correction?: string;
  assistant_text?: string;
  audio_output_url?: string;
  stt_latency_ms?: number;
  tts_latency_ms?: number;
}

export interface ConversationDetails extends Conversation {
  turns: Turn[];
}

export interface UnknownTerm {
  id: string;
  language: 'ru' | 'kk';
  heard_variant: string;
  correct_form: string;
  context_examples: string[];
  provider_where_seen?: string;
  occurrence_count: number;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  updated_at: string;
}

export interface ProviderMetrics {
  provider: string;
  total_requests: number;
  avg_confidence: number;
  avg_stt_latency_ms: number;
  avg_tts_latency_ms: number;
  correction_rate: number;
}

export interface ConversationFilter {
  user_id?: string;
  provider?: string;
  date_from?: string;
  date_to?: string;
  low_confidence?: boolean;
}

// Admin API
export const adminApi = {
  // Users
  getUsers: async (): Promise<User[]> => {
    const response = await api.get('/api/admin/users');
    return response.data;
  },

  updateUser: async (
    userId: string,
    data: { stt_provider?: string; tts_provider?: string }
  ): Promise<User> => {
    const response = await api.patch(`/api/admin/users/${userId}`, data);
    return response.data;
  },

  // Conversations
  getConversations: async (filter?: ConversationFilter): Promise<Conversation[]> => {
    const response = await api.get('/api/admin/conversations', { params: filter });
    return response.data;
  },

  getConversation: async (id: string): Promise<ConversationDetails> => {
    const response = await api.get(`/api/admin/conversations/${id}`);
    return response.data;
  },

  // Unknown Terms
  getUnknownTerms: async (status?: string): Promise<UnknownTerm[]> => {
    const response = await api.get('/api/admin/unknown-terms', { params: { status } });
    return response.data;
  },

  createUnknownTerm: async (data: {
    language: string;
    heard_variant: string;
    correct_form: string;
  }): Promise<UnknownTerm> => {
    const response = await api.post('/api/admin/unknown-terms', data);
    return response.data;
  },

  approveTerm: async (id: string): Promise<UnknownTerm> => {
    const response = await api.patch(`/api/admin/unknown-terms/${id}/approve`);
    return response.data;
  },

  rejectTerm: async (id: string): Promise<UnknownTerm> => {
    const response = await api.patch(`/api/admin/unknown-terms/${id}/reject`);
    return response.data;
  },

  // Analytics
  getAnalytics: async (): Promise<{ metrics: ProviderMetrics[]; top_unknown_terms: { term: string; count: number }[] }> => {
    const response = await api.get('/api/admin/analytics');
    return response.data;
  },
};

export default api;
