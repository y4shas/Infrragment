import { useState, useRef, useCallback, useEffect } from 'react';
import { uploadPDF, listUploads } from '../api/client';

export default function UploadView({ onUploadStarted, onViewResults }) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [previousUploads, setPreviousUploads] = useState([]);
  const [loadingUploads, setLoadingUploads] = useState(true);
  const inputRef = useRef(null);

  useEffect(() => {
    listUploads()
      .then((data) => setPreviousUploads(data.uploads || []))
      .catch(() => setPreviousUploads([]))
      .finally(() => setLoadingUploads(false));
  }, []);

  const handleFile = useCallback((f) => {
    setError(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are accepted');
      return;
    }
    setFile(f);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    handleFile(f);
  }, [handleFile]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      const data = await uploadPDF(file);
      onUploadStarted(data);
    } catch (err) {
      setError(err.message);
      setIsUploading(false);
    }
  }, [file, onUploadStarted]);

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatTime = (seconds) => {
    if (!seconds) return '—';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-16 animate-slide-up">
      {/* Hero */}
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-100">
          Document Structuring
        </h1>
        <p className="mt-3 text-lg text-slate-400">
          Upload a multi-document PDF to split, classify, and extract tables automatically.
        </p>
      </div>

      {/* Drop zone */}
      <div
        className={`
          relative rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer
          ${isDragging
            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.02]'
            : file
              ? 'border-emerald-500/40 bg-emerald-500/5'
              : 'border-slate-700/60 bg-slate-800/30 hover:border-slate-600 hover:bg-slate-800/50'
          }
        `}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !file && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

        <div className="flex flex-col items-center justify-center px-6 py-16">
          {!file ? (
            <>
              {/* Upload icon */}
              <div className={`mb-6 rounded-2xl p-4 ${isDragging ? 'bg-indigo-500/20' : 'bg-slate-800/80'} transition-colors`}>
                <svg className={`h-10 w-10 ${isDragging ? 'text-indigo-400' : 'text-slate-500'} transition-colors`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
              </div>
              <p className="text-base font-medium text-slate-300">
                Drop your PDF here
              </p>
              <p className="mt-1.5 text-sm text-slate-500">
                or <span className="text-indigo-400 hover:text-indigo-300 cursor-pointer">browse files</span>
              </p>
            </>
          ) : (
            <>
              {/* File selected */}
              <div className="mb-4 rounded-2xl bg-emerald-500/10 p-4">
                <svg className="h-10 w-10 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <p className="text-base font-medium text-slate-200">{file.name}</p>
              <p className="mt-1 text-sm text-slate-500">{formatSize(file.size)}</p>
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                className="mt-3 text-xs text-slate-500 hover:text-rose-400 transition-colors"
              >
                Remove
              </button>
            </>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-xl bg-rose-500/10 border border-rose-500/20 px-4 py-3 text-sm text-rose-400 animate-fade-in">
          {error}
        </div>
      )}

      {/* Upload button */}
      {file && (
        <div className="mt-6 flex justify-center animate-fade-in">
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className={`
              inline-flex items-center gap-2.5 rounded-xl px-8 py-3 text-sm font-semibold transition-all duration-200
              ${isUploading
                ? 'bg-indigo-500/40 text-indigo-300 cursor-wait'
                : 'bg-indigo-600 text-white hover:bg-indigo-500 hover:shadow-lg hover:shadow-indigo-500/25 active:scale-[0.98]'
              }
            `}
          >
            {isUploading ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                  <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                </svg>
                Uploading…
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Process Document
              </>
            )}
          </button>
        </div>
      )}

      {/* Previous uploads */}
      <div className="mt-16">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-500">
          Previous Uploads
        </h2>
        {loadingUploads ? (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
              <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
            </svg>
            Loading…
          </div>
        ) : previousUploads.length === 0 ? (
          <p className="text-sm text-slate-600">No processed uploads yet.</p>
        ) : (
          <div className="space-y-2 stagger-children">
            {previousUploads.map((u) => (
              <button
                key={u.upload_id}
                onClick={() => onViewResults(u.upload_id)}
                className="group flex w-full items-center justify-between rounded-xl border border-slate-800/60 bg-slate-800/30 px-5 py-4 text-left transition-all hover:border-slate-700 hover:bg-slate-800/60"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-200 group-hover:text-indigo-400 transition-colors">
                    {u.source_filename}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {u.total_pages} pages · {u.document_count} documents · {formatTime(u.processing_time_seconds)}
                  </p>
                </div>
                <div className="ml-4 flex items-center gap-2">
                  <span className="rounded-md bg-slate-700/50 px-2 py-0.5 text-xs font-mono text-slate-400">
                    {u.upload_id}
                  </span>
                  <svg className="h-4 w-4 text-slate-600 group-hover:text-indigo-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
