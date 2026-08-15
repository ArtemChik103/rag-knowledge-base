import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

export function DocUploader({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUploaded, setLastUploaded] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = async (e) => {
    if (e.target.files && e.target.files.length > 0) {
      await uploadFile(e.target.files[0]);
      e.target.value = '';
    }
  };

  const uploadFile = async (file) => {
    setError(null);
    setLastUploaded(null);
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Ошибка при загрузке файла');
      }

      const data = await res.json();
      setLastUploaded(data.document);
      if (onUploadSuccess) onUploadSuccess(data.document);
    } catch (err) {
      setError(err.message || 'Сбой при загрузке документа');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? 'border-brand-400 bg-brand-950/20'
            : 'border-zinc-800 hover:border-zinc-700 bg-zinc-900/40 hover:bg-zinc-900/70'
        } ${uploading ? 'opacity-60 cursor-wait' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,.markdown"
          onChange={handleFileSelect}
          className="hidden"
          disabled={uploading}
        />

        <div className="flex flex-col items-center justify-center space-y-2.5">
          <div className="h-10 w-10 rounded-full bg-zinc-800/80 border border-zinc-700 flex items-center justify-center text-zinc-300 group-hover:text-brand-400">
            {uploading ? (
              <Loader2 className="h-5 w-5 animate-spin text-brand-400" />
            ) : (
              <UploadCloud className="h-5 w-5" />
            )}
          </div>

          <div className="space-y-1">
            <p className="text-xs font-medium text-zinc-200">
              {uploading ? 'Индексация и векторизация...' : 'Перетащите PDF, TXT или MD'}
            </p>
            <p className="text-[11px] text-zinc-500 font-mono">
              до 50 МБ • автоматический сплит и эмбеддинги
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center space-x-2 text-xs text-red-400 bg-red-950/30 border border-red-900/50 px-3 py-2 rounded-lg">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {lastUploaded && (
        <div className="flex items-center justify-between text-xs text-zinc-300 bg-zinc-900/90 border border-zinc-800 px-3 py-2 rounded-lg animate-fade-in">
          <div className="flex items-center space-x-2 truncate">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="truncate font-medium">{lastUploaded.filename}</span>
          </div>
          <span className="text-[11px] font-mono text-zinc-500 shrink-0">
            +{lastUploaded.total_chunks} чанков
          </span>
        </div>
      )}
    </div>
  );
}
