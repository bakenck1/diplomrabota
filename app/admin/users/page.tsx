'use client';

import { useEffect, useState } from 'react';
import { adminApi, User } from '@/services/api';

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ stt_provider: '', tts_provider: '' });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await adminApi.getUsers();
      setUsers(data);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (user: User) => {
    setEditingId(user.id);
    setEditForm({ stt_provider: user.stt_provider, tts_provider: user.tts_provider });
  };

  const saveEdit = async (userId: string) => {
    try {
      await adminApi.updateUser(userId, editForm);
      setEditingId(null);
      loadUsers();
    } catch (err) {
      console.error('Failed to update user:', err);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Загрузка...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Пользователи</h1>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Имя</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Роль</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Язык</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">STT</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">TTS</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Тест</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="font-medium text-gray-900">{user.name}</div>
                  <div className="text-sm text-gray-500">
                    {user.last_active_at
                      ? `Активен: ${new Date(user.last_active_at).toLocaleDateString()}`
                      : 'Не активен'}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 text-xs rounded-full ${
                      user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {user.role}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-600">{user.language.toUpperCase()}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {editingId === user.id ? (
                    <select
                      value={editForm.stt_provider}
                      onChange={(e) => setEditForm({ ...editForm, stt_provider: e.target.value })}
                      className="border rounded px-2 py-1 text-sm"
                    >
                      <option value="openai">OpenAI</option>
                      <option value="google">Google</option>
                    </select>
                  ) : (
                    <span className="text-gray-600">{user.stt_provider}</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {editingId === user.id ? (
                    <select
                      value={editForm.tts_provider}
                      onChange={(e) => setEditForm({ ...editForm, tts_provider: e.target.value })}
                      className="border rounded px-2 py-1 text-sm"
                    >
                      <option value="openai">OpenAI</option>
                      <option value="google">Google</option>
                    </select>
                  ) : (
                    <span className="text-gray-600">{user.tts_provider}</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {user.is_test_user && <span className="text-blue-600">✓</span>}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {editingId === user.id ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => saveEdit(user.id)}
                        className="text-green-600 hover:text-green-800 text-sm"
                      >
                        Сохранить
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="text-gray-600 hover:text-gray-800 text-sm"
                      >
                        Отмена
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => startEdit(user)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      Изменить
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
