import React, { useState } from 'react';
import { Search, Sparkles, Clock, Compass, FileText, ChevronDown, ChevronUp, CheckCircle2, CornerDownLeft, Loader2 } from 'lucide-react';

export function QueryView({ onQuery, loading, result, lastQuery }) {
  const [inputText, setInputText] = useState('');
  const [expandedCitation, setExpandedCitation] = useState(null);

  const sampleQuestions = [
    "Каков рабочий график и время обеденного перерыва?",
    "Какие требования к удаленной работе и корпоративному VPN?",
    "Каков размер компенсации на спорт и профессиональное обучение?",
    "Что запрещено подключать к рабочим компьютерам и каковы требования к паролям?",
    "Сколько дней составляет отпуск и как оформить больничный или Day-off?",
  ];

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!inputText.trim() || loading) return;
    onQuery(inputText.trim());
  };

  const handleSelectSample = (q) => {
    setInputText(q);
    onQuery(q);
  };

  const toggleCitation = (idx) => {
    setExpandedCitation(expandedCitation === idx ? null : idx);
  };

  return (
    <div className="space-y-6">
      {/* Поисковая строка ввода */}
      <div className="space-y-2">
        <form onSubmit={handleSubmit} className="relative">
          <div className="relative flex items-center">
            <Search className="absolute left-4 h-4 w-4 text-zinc-400 pointer-events-none" />
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Задайте вопрос по базе знаний (например: каков размер компенсации на спорт?)..."
              disabled={loading}
              className="w-full pl-11 pr-24 py-3 bg-zinc-900/90 hover:bg-zinc-900 focus:bg-zinc-900 border border-zinc-800 focus:border-brand-500 rounded-xl text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-brand-500 transition-all font-sans"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || loading}
              className="absolute right-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-500 hover:bg-brand-600 text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center space-x-1"
            >
              {loading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Поиск</span>
                </>
              ) : (
                <>
                  <span>Спросить</span>
                  <CornerDownLeft className="h-3 w-3" />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Быстрые подсказки-вопросы */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 text-xs text-zinc-400 no-scrollbar">
          <span className="text-[11px] uppercase font-mono text-zinc-500 shrink-0">Частые вопросы:</span>
          {sampleQuestions.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSelectSample(q)}
              disabled={loading}
              className="shrink-0 px-2.5 py-1 rounded-md bg-zinc-900/60 hover:bg-zinc-800/80 text-zinc-400 hover:text-zinc-200 border border-zinc-800 text-[11px] transition-colors"
            >
              {q.length > 38 ? q.slice(0, 38) + '...' : q}
            </button>
          ))}
        </div>
      </div>

      {/* Отображение результата поиска */}
      {result && (
        <div className="space-y-5 animate-fade-in">
          {/* Карточка ответа */}
          <div className="rounded-xl border border-zinc-800/90 bg-zinc-900/40 p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2 text-xs font-medium text-brand-400">
                <Sparkles className="h-4 w-4" />
                <span>Сгенерированный ответ</span>
              </div>

              {/* Бейдж оценки уверенности */}
              <div className="flex items-center space-x-2 text-xs font-mono">
                <span className="text-zinc-500">Уверенность:</span>
                <span className={`px-2 py-0.5 rounded font-medium ${
                  result.confidence_score > 0.5
                    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60'
                    : result.confidence_score > 0.25
                    ? 'bg-amber-950/60 text-amber-300 border border-amber-800/60'
                    : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                }`}>
                  {(result.confidence_score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Текст ответа */}
            <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-line font-sans pl-1">
              {result.answer}
            </div>

            {/* Строка метрик и телеметрии */}
            <div className="pt-3 border-t border-zinc-800/60 flex flex-wrap items-center justify-between text-[11px] font-mono text-zinc-500 gap-2">
              <div className="flex items-center space-x-3">
                <span className="flex items-center space-x-1">
                  <Clock className="h-3 w-3" />
                  <span>Всего: {result.total_time_ms} ms</span>
                </span>
                <span>(Поиск: {result.retrieval_time_ms} ms, Ответ: {result.generation_time_ms} ms)</span>
              </div>
              <div>
                <span>Найдено фрагментов: {result.retrieved_chunks_count}</span>
              </div>
            </div>
          </div>

          {/* Секция источников и цитат */}
          {result.citations && result.citations.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 font-mono">
                  Источники и контекстные фрагменты ({result.citations.length})
                </h3>
              </div>

              <div className="grid grid-cols-1 gap-2.5">
                {result.citations.map((cit, idx) => {
                  const isExpanded = expandedCitation === idx;
                  return (
                    <div
                      key={cit.chunk_id || idx}
                      className="rounded-lg border border-zinc-800/80 bg-zinc-900/60 hover:border-zinc-700 transition-all text-xs overflow-hidden"
                    >
                      <button
                        type="button"
                        onClick={() => toggleCitation(idx)}
                        className="w-full flex items-center justify-between p-3 text-left hover:bg-zinc-800/30 transition-colors"
                      >
                        <div className="flex items-center space-x-2.5 min-w-0 pr-2">
                          <FileText className="h-3.5 w-3.5 text-zinc-400 shrink-0" />
                          <span className="font-medium text-zinc-200 truncate">
                            {cit.filename}
                          </span>
                          {cit.page_number && (
                            <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px] shrink-0">
                              Стр. {cit.page_number}
                            </span>
                          )}
                          <span className="px-1.5 py-0.5 rounded bg-zinc-800/60 text-zinc-400 font-mono text-[10px] shrink-0">
                            #{cit.chunk_index}
                          </span>
                        </div>

                        <div className="flex items-center space-x-2 shrink-0">
                          <span className="text-[11px] font-mono text-brand-400">
                            {(cit.score * 100).toFixed(1)}% match
                          </span>
                          {isExpanded ? (
                            <ChevronUp className="h-3.5 w-3.5 text-zinc-500" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
                          )}
                        </div>
                      </button>

                      <div className={`px-3.5 pb-3 text-zinc-300 leading-relaxed font-sans text-xs bg-zinc-950/40 border-t border-zinc-800/40 pt-2 ${
                        isExpanded ? 'block' : 'line-clamp-2'
                      }`}>
                        {cit.snippet}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Начальное пустое состояние */}
      {!result && !loading && (
        <div className="rounded-xl border border-zinc-800/40 bg-zinc-900/10 p-12 text-center space-y-3">
          <div className="h-10 w-10 mx-auto rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500">
            <Compass className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-zinc-300">Готов к поиску по базе знаний</p>
            <p className="text-xs text-zinc-500 max-w-md mx-auto">
              Задайте вопрос в поисковой строке или выберите один из готовых сценариев выше для тестирования RAG-конвейера.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
