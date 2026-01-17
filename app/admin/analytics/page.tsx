'use client';

import { useEffect, useState } from 'react';
import { adminApi, ProviderMetrics } from '@/services/api';

interface AnalyticsData {
  metrics: ProviderMetrics[];
  top_unknown_terms: { term: string; count: number }[];
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      const result = await adminApi.getAnalytics();
      setData(result);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Загрузка...</div>;
  }

  if (!data) {
    return <div className="text-center py-8 text-red-600">Ошибка загрузки данных</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Аналитика</h1>

      {/* Provider metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {data.metrics.map((metric) => (
          <div key={metric.provider} className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span
                className={`w-3 h-3 rounded-full ${
                  metric.provider === 'openai' ? 'bg-green-500' : 'bg-blue-500'
                }`}
              />
              {metric.provider.toUpperCase()}
            </h2>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded p-3">
                <p className="text-sm text-gray-500">Всего запросов</p>
                <p className="text-2xl font-bold text-gray-800">{metric.total_requests}</p>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <p className="text-sm text-gray-500">Средний confidence</p>
                <p className="text-2xl font-bold text-gray-800">
                  {(metric.avg_confidence * 100).toFixed(1)}%
                </p>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <p className="text-sm text-gray-500">STT latency</p>
                <p className="text-2xl font-bold text-gray-800">{metric.avg_stt_latency_ms}ms</p>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <p className="text-sm text-gray-500">TTS latency</p>
                <p className="text-2xl font-bold text-gray-800">{metric.avg_tts_latency_ms}ms</p>
              </div>
              <div className="bg-gray-50 rounded p-3 col-span-2">
                <p className="text-sm text-gray-500">Процент исправлений</p>
                <p className="text-2xl font-bold text-gray-800">
                  {(metric.correction_rate * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
        ))}

        {data.metrics.length === 0 && (
          <div className="col-span-2 bg-white rounded-lg shadow p-6 text-center text-gray-500">
            Нет данных по провайдерам
          </div>
        )}
      </div>

      {/* Comparison chart placeholder */}
      {data.metrics.length >= 2 && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-bold text-gray-800 mb-4">Сравнение провайдеров</h2>
          <div className="space-y-4">
            {/* Confidence comparison */}
            <div>
              <p className="text-sm text-gray-600 mb-2">Confidence</p>
              <div className="flex gap-2 items-center">
                {data.metrics.map((m) => (
                  <div key={m.provider} className="flex-1">
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>{m.provider}</span>
                      <span>{(m.avg_confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-4 bg-gray-200 rounded overflow-hidden">
                      <div
                        className={`h-full ${m.provider === 'openai' ? 'bg-green-500' : 'bg-blue-500'}`}
                        style={{ width: `${m.avg_confidence * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Latency comparison */}
            <div>
              <p className="text-sm text-gray-600 mb-2">STT Latency (меньше = лучше)</p>
              <div className="flex gap-2 items-center">
                {data.metrics.map((m) => {
                  const maxLatency = Math.max(...data.metrics.map((x) => x.avg_stt_latency_ms));
                  return (
                    <div key={m.provider} className="flex-1">
                      <div className="flex justify-between text-xs text-gray-500 mb-1">
                        <span>{m.provider}</span>
                        <span>{m.avg_stt_latency_ms}ms</span>
                      </div>
                      <div className="h-4 bg-gray-200 rounded overflow-hidden">
                        <div
                          className={`h-full ${m.provider === 'openai' ? 'bg-green-500' : 'bg-blue-500'}`}
                          style={{ width: `${(m.avg_stt_latency_ms / maxLatency) * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top unknown terms */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-800 mb-4">Топ непонятных слов</h2>
        {data.top_unknown_terms.length > 0 ? (
          <div className="space-y-2">
            {data.top_unknown_terms.map((item, idx) => (
              <div
                key={item.term}
                className="flex items-center justify-between py-2 border-b last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className="text-gray-400 text-sm w-6">{idx + 1}.</span>
                  <span className="font-medium text-gray-800">{item.term}</span>
                </div>
                <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-sm">
                  {item.count} раз
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">Нет данных</p>
        )}
      </div>
    </div>
  );
}
