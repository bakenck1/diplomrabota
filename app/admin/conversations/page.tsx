'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { adminApi, Conversation, ConversationFilter, User } from '@/services/api';

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<ConversationFilter>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [convs, usrs] = await Promise.all([
        adminApi.getConversations(filter),
        adminApi.getUsers(),
      ]);
      setConversations(convs);
      setUsers(usrs);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const applyFilter = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getConversations(filter);
      setConversations(data);
    } catch (err) {
      console.error('Failed to filter:', err);
    } finally {
      setLoading(false);
    }
  };

  const getUserName = (userId: string) => {
    const user = users.find((u) => u.id === userId);
    return user?.name || userId.slice(0, 8);
  };

  if (loading && conversations.length === 0) {
    return <div className="text-center py-8">Загрузка...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Диалоги</h1>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Пользователь</label>
            <select
              value={filter.user_id || ''}
              onChange={(e) => setFilter({ ...filter, user_id: e.target.value || undefined })}
              className="border rounded px-3 py-2 text-sm"
            >
              <option value="">Все</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Провайдер</label>
            <select
              value={filter.provider || ''}
              onChange={(e) => setFilter({ ...filter, provider: e.target.value || undefined })}
              className="border rounded px-3 py-2 text-sm"
            >
              <option value="">Все</option>
              <option value="openai">OpenAI</option>
              <option value="google">Google</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">С даты</label>
            <input
              type="date"
              value={filter.date_from || ''}
              onChange={(e) => setFilter({ ...filter, date_from: e.target.value || undefined })}
              className="border rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">По дату</label>
            <input
              type="date"
              value={filter.date_to || ''}
              onChange={(e) => setFilter({ ...filter, date_to: e.target.value || undefined })}
              className="border rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="lowConf"
              checked={filter.low_confidence || false}
              onChange={(e) => setFilter({ ...filter, low_confidence: e.target.checked || undefined })}
            />
            <label htmlFor="lowConf" className="text-sm text-gray-600">Низкий confidence</label>
          </div>
          <button
            onClick={applyFilter}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
          >
            Применить
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Дата</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Пользователь</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">STT</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">TTS</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Шагов</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {conversations.map((conv) => (
              <tr key={conv.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {new Date(conv.started_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {conv.user_name || getUserName(conv.user_id)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {conv.stt_provider_used}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {conv.tts_provider_used}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {conv.turn_count}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link
                    href={`/admin/conversations/${conv.id}`}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    Подробнее
                  </Link>
                </td>
              </tr>
            ))}
            {conversations.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  Диалоги не найдены
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
