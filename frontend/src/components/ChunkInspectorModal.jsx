import React, { useEffect, useState } from 'react';
import { X, Layers, Loader2, FileText, Hash } from 'lucide-react';

export function ChunkInspectorModal({ doc, onClose }) {
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!doc) return;
    const fetchChunks = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/documents/${doc.doc_id}/chunks`);
        if (!res.ok) throw new Error('Не удалось загрузить чанки документа');
        const data = await res.json();
        setChunks(data);
      } catch (err) {
        setError(err.message || 'Ошибка загрузки');
      } finally {
        setLoading(false);
      }
    };
    fetchChunks();
  }, [doc]);

  if (!doc) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-3xl max-h-[85vh] rounded-xl bg-zinc-950 border border-zinc-800 shadow-2xl flex flex-col overflow-hidden">
        {/* Шапка модального окна */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center space-x-2.5 min-w-0 pr-4">
            <Layers className="h-4 w-4 text-brand-400 shrink-0" />
            <div className="truncate">
              <h2 className="text-sm font-semibold text-zinc-100 truncate">
                Инспектор чанков: {doc.filename}
              </h2>
              <p className="text-[11px] font-mono text-zinc-500">
                {chunks.length} фрагментов в векторном индексе ChromaDB
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Закрыть</span>
          </button>
        </div>

        {/* Тело модального окна */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center space-y-2 text-zinc-400">
              <Loader2 className="h-5 w-5 animate-spin text-brand-400" />
              <p className="text-xs font-mono">Загрузка фрагментов из векторной базы...</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-lg bg-red-950/40 border border-red-900/60 text-xs text-red-300">
              {error}
            </div>
          )}

          {!loading && !error && chunks.map((c) => (
            <div
              key={c.chunk_id}
              className="p-3.5 rounded-lg bg-zinc-900/60 border border-zinc-800/80 space-y-2 text-xs"
            >
              <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 pb-1.5 border-b border-zinc-800/50">
                <span className="flex items-center space-x-1 text-zinc-400 font-medium">
                  <Hash className="h-3 w-3" />
                  <span>Чанк #{c.chunk_index}</span>
                </span>
                <div className="flex items-center space-x-3">
                  {c.page_number && <span>Стр. {c.page_number}</span>}
                  <span>{c.char_count} символов</span>
                </div>
              </div>
              <p className="text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap">
                {c.text}
              </p>
            </div>
          ))}
        </div>

        {/* Подвал модального окна */}
        <div className="px-5 py-3 border-t border-zinc-800 bg-zinc-900/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}
