'use client';

import { useEffect, useState } from 'react';
import { adminApi, UnknownTerm } from '@/services/api';

export default function TermsPage() {
  const [terms, setTerms] = useState<UnknownTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTerm, setNewTerm] = useState({ language: 'ru', heard_variant: '', correct_form: '' });

  useEffect(() => {
    loadTerms();
  }, [statusFilter]);

  const loadTerms = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getUnknownTerms(statusFilter || undefined);
      setTerms(data);
    } catch (err) {
      console.error('Failed to load terms:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await adminApi.approveTerm(id);
      loadTerms();
    } catch (err) {
      console.error('Failed to approve term:', err);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await adminApi.rejectTerm(id);
      loadTerms();
    } catch (err) {
      console.error('Failed to reject term:', err);
    }
  };

  const handleAddTerm = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminApi.createUnknownTerm(newTerm);
      setNewTerm({ language: 'ru', heard_variant: '', correct_form: '' });
      setShowAddForm(false);
      loadTerms();
    } catch (err) {
      console.error('Failed to add term:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
    };
    return styles[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Словарь терминов</h1>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
        >
          {showAddForm ? 'Отмена' : '+ Добавить термин'}
        </button>
      </div>

      {/* Add form */}
      {showAddForm && (
        <form onSubmit={handleAddTerm} className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Язык</label>
              <select
                value={newTerm.language}
                onChange={(e) => setNewTerm({ ...newTerm, language: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="ru">Русский</option>
                <option value="kk">Казахский</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Услышанный вариант</label>
              <input
                type="text"
                value={newTerm.heard_variant}
                onChange={(e) => setNewTerm({ ...newTerm, heard_variant: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Правильная форма</label>
              <input
                type="text"
                value={newTerm.correct_form}
                onChange={(e) => setNewTerm({ ...newTerm, correct_form: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm w-full"
              >
                Добавить
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Filter */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-center">
          <label className="text-sm text-gray-600">Статус:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">Все</option>
            <option value="pending">Ожидают</option>
            <option value="approved">Одобрены</option>
            <option value="rejected">Отклонены</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-8">Загрузка...</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Услышано</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Правильно</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Язык</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Провайдер</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Кол-во</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {terms.map((term) => (
                <tr key={term.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                    {term.heard_variant}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">{term.correct_form}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">{term.language.toUpperCase()}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                    {term.provider_where_seen || '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">{term.occurrence_count}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadge(term.status)}`}>
                      {term.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {term.status === 'pending' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApprove(term.id)}
                          className="text-green-600 hover:text-green-800 text-sm"
                        >
                          ✓ Одобрить
                        </button>
                        <button
                          onClick={() => handleReject(term.id)}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          ✗ Отклонить
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {terms.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                    Термины не найдены
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
