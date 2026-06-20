import { useState, useEffect } from 'react';
import { getDocuments } from '../api/client';
import DocumentBrowser from './DocumentBrowser';
import DocumentDetail from './DocumentDetail';
import EfficiencyPanel from './EfficiencyPanel';

export default function ResultsView({ uploadId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [showEfficiency, setShowEfficiency] = useState(false);

  useEffect(() => {
    if (!uploadId) return;
    setLoading(true);
    setError(null);
    getDocuments(uploadId)
      .then((d) => {
        setData(d);
        // Auto-select first document
        if (d.documents?.length > 0) {
          setSelectedDoc(d.documents[0]);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [uploadId]);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <svg className="h-8 w-8 animate-spin text-indigo-500" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
            <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
          </svg>
          <p className="text-sm text-slate-500">Loading results…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-6 py-4 text-center">
          <p className="text-sm text-rose-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col animate-fade-in">
      {/* Summary bar */}
      <div className="flex-shrink-0 border-b border-slate-800/60 bg-slate-950/60 px-6 py-3">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between">
          <div className="flex items-center gap-6">
            <div>
              <p className="text-sm font-medium text-slate-200 truncate max-w-xs">
                {data.source_filename}
              </p>
              <p className="text-xs text-slate-500">
                {data.total_pages} pages · {data.document_count} documents
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowEfficiency(!showEfficiency)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
              showEfficiency
                ? 'bg-indigo-500/20 text-indigo-400'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-300'
            }`}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
            Efficiency
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <DocumentBrowser
          documents={data.documents}
          selectedDoc={selectedDoc}
          onSelectDoc={setSelectedDoc}
        />

        {/* Detail view */}
        <div className="flex-1 overflow-hidden">
          {selectedDoc ? (
            <DocumentDetail
              uploadId={uploadId}
              document={selectedDoc}
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-slate-600">Select a document to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Efficiency panel */}
      {showEfficiency && (
        <EfficiencyPanel uploadId={uploadId} onClose={() => setShowEfficiency(false)} />
      )}
    </div>
  );
}
