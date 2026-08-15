import React from 'react';
import { FileText, Eye, Trash2, Layers } from 'lucide-react';

export function DocList({ documents, onInspectChunks, onDeleteDoc, deletingId }) {
  if (!documents || documents.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/20 p-6 text-center">
        <p className="text-xs text-zinc-500">
          В базе знаний пока нет документов. Загрузите PDF или нажмите «Демо-регламент PDF».
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
      {documents.map((doc) => (
        <div
          key={doc.doc_id}
          className="group flex items-center justify-between p-3 rounded-lg bg-zinc-900/70 hover:bg-zinc-900 border border-zinc-800/80 hover:border-zinc-700 transition-all text-xs"
        >
          <div className="flex items-center space-x-2.5 truncate min-w-0 pr-2">
            <div className="h-7 w-7 rounded bg-zinc-800 flex items-center justify-center text-zinc-400 shrink-0">
              <FileText className="h-3.5 w-3.5" />
            </div>
            <div className="truncate">
              <p className="font-medium text-zinc-200 truncate" title={doc.filename}>
                {doc.filename}
              </p>
              <div className="flex items-center space-x-2 text-[11px] font-mono text-zinc-500">
                <span>{doc.total_pages} стр.</span>
                <span>•</span>
                <span>{doc.chunk_count} чанков</span>
                <span>•</span>
                <span>{(doc.total_chars / 1024).toFixed(1)} КБ</span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-1 shrink-0">
            <button
              onClick={() => onInspectChunks(doc)}
              title="Просмотреть векторизованные чанки"
              className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
            >
              <Layers className="h-3.5 w-3.5" />
              <span className="sr-only">Чанки</span>
            </button>
            <button
              onClick={() => onDeleteDoc(doc.doc_id)}
              disabled={deletingId === doc.doc_id}
              title="Удалить документ"
              className="p-1.5 rounded-md text-zinc-500 hover:text-red-400 hover:bg-red-950/30 transition-colors disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span className="sr-only">Удалить</span>
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
