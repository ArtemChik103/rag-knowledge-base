import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { DocUploader } from './components/DocUploader';
import { DocList } from './components/DocList';
import { QueryView } from './components/QueryView';
import { ChunkInspectorModal } from './components/ChunkInspectorModal';
import { FileText, Search, Database } from 'lucide-react';

export default function App() {
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loadingSample, setLoadingSample] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState(null);
  const [lastQuery, setLastQuery] = useState('');
  const [inspectingDoc, setInspectingDoc] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error('Failed to fetch stats', e);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (e) {
      console.error('Failed to fetch documents', e);
    }
  };

  const refreshAll = () => {
    fetchStats();
    fetchDocuments();
  };

  useEffect(() => {
    refreshAll();
  }, []);

  const handleGenerateSample = async () => {
    setLoadingSample(true);
    try {
      const res = await fetch('/api/sample-document', { method: 'POST' });
      if (res.ok) {
        refreshAll();
      }
    } catch (e) {
      console.error('Sample generation failed', e);
    } finally {
      setLoadingSample(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Вы действительно хотите очистить всю базу знаний и удалить все векторы?')) {
      return;
    }
    setResetting(true);
    try {
      const res = await fetch('/api/reset', { method: 'POST' });
      if (res.ok) {
        setQueryResult(null);
        refreshAll();
      }
    } catch (e) {
      console.error('Reset failed', e);
    } finally {
      setResetting(false);
    }
  };

  const handleDeleteDoc = async (docId) => {
    setDeletingId(docId);
    try {
      const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        refreshAll();
      }
    } catch (e) {
      console.error('Delete failed', e);
    } finally {
      setDeletingId(null);
    }
  };

  const handleQuery = async (queryText) => {
    setQueryLoading(true);
    setLastQuery(queryText);
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, top_k: 4 }),
      });
      if (res.ok) {
        const data = await res.json();
        setQueryResult(data);
      }
    } catch (e) {
      console.error('Query failed', e);
    } finally {
      setQueryLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans">
      <Header
        stats={stats}
        onReset={handleReset}
        onGenerateSample={handleGenerateSample}
        loadingSample={loadingSample}
        resetting={resetting}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Knowledge Base & Upload (4 cols) */}
          <section className="lg:col-span-4 space-y-5">
            {/* Upload Box */}
            <div className="rounded-xl border border-zinc-800/90 bg-zinc-900/40 p-4 space-y-3">
              <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-zinc-400 font-mono">
                <FileText className="h-4 w-4 text-brand-400" />
                <span>Загрузка документа</span>
              </div>
              <DocUploader onUploadSuccess={refreshAll} />
            </div>

            {/* Ingested Documents List */}
            <div className="rounded-xl border border-zinc-800/90 bg-zinc-900/40 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-zinc-400 font-mono">
                  <Database className="h-4 w-4 text-zinc-400" />
                  <span>База документов ({documents.length})</span>
                </div>
              </div>
              <DocList
                documents={documents}
                onInspectChunks={(doc) => setInspectingDoc(doc)}
                onDeleteDoc={handleDeleteDoc}
                deletingId={deletingId}
              />
            </div>
          </section>

          {/* Right Column: Search & Q&A Workspace (8 cols) */}
          <section className="lg:col-span-8">
            <div className="rounded-xl border border-zinc-800/90 bg-zinc-900/40 p-5">
              <div className="flex items-center space-x-2 pb-4 mb-4 border-b border-zinc-800/70 text-xs font-semibold uppercase tracking-wider text-zinc-400 font-mono">
                <Search className="h-4 w-4 text-brand-400" />
                <span>Интеллектуальный поиск и генерация ответа</span>
              </div>

              <QueryView
                onQuery={handleQuery}
                loading={queryLoading}
                result={queryResult}
                lastQuery={lastQuery}
              />
            </div>
          </section>
        </div>
      </main>

      {/* Chunk Inspector Modal */}
      {inspectingDoc && (
        <ChunkInspectorModal
          doc={inspectingDoc}
          onClose={() => setInspectingDoc(null)}
        />
      )}
    </div>
  );
}
