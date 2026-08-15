import React from 'react';
import { Database, FileText, RefreshCw, Sparkles, Trash2, Cpu } from 'lucide-react';

export function Header({ stats, onReset, onGenerateSample, loadingSample, resetting }) {
  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Левая часть: Логотип и заголовок */}
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-zinc-900 border border-zinc-700/80 flex items-center justify-center text-brand-400 shadow-sm">
            <Database className="h-4.5 w-4.5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-semibold tracking-tight text-zinc-100">
                RAG Knowledge Base
              </h1>
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                v1.0
              </span>
            </div>
            <p className="text-xs text-zinc-400 hidden sm:block">
              Семантический поиск и Q&A по корпоративным регламентам
            </p>
          </div>
        </div>

        {/* Центр: Системная телеметрия */}
        <div className="hidden md:flex items-center space-x-4 text-xs font-mono text-zinc-400">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-zinc-900/90 border border-zinc-800">
            <FileText className="h-3.5 w-3.5 text-zinc-400" />
            <span>{stats?.total_documents || 0} док.</span>
            <span className="text-zinc-600">•</span>
            <span>{stats?.total_chunks || 0} чанков</span>
          </div>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-zinc-900/90 border border-zinc-800">
            <Cpu className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-zinc-300 truncate max-w-[160px]" title={stats?.embedding_model || 'Local Embeddings'}>
              {stats?.embedding_model ? stats.embedding_model.split('/').pop() : 'paraphrase-multilingual'}
            </span>
          </div>
        </div>

        {/* Правая часть: Действия */}
        <div className="flex items-center space-x-2">
          <button
            onClick={onGenerateSample}
            disabled={loadingSample}
            title="Сгенерировать и проиндексировать образец регламента ООО «ТехноИнновации»"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700/80 hover:border-zinc-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Sparkles className={`h-3.5 w-3.5 text-brand-400 ${loadingSample ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Демо-регламент PDF</span>
            <span className="sm:hidden">Демо PDF</span>
          </button>

          <button
            onClick={onReset}
            disabled={resetting}
            title="Очистить векторную базу знаний"
            className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-zinc-900 hover:bg-red-950/40 text-zinc-400 hover:text-red-300 border border-zinc-800 hover:border-red-800/60 transition-all disabled:opacity-50"
          >
            <Trash2 className={`h-3.5 w-3.5 ${resetting ? 'animate-spin' : ''}`} />
            <span className="sr-only">Сброс</span>
          </button>
        </div>
      </div>
    </header>
  );
}
