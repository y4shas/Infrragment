import { useState, useEffect } from 'react';
import { getDocumentPdfUrl, getDocumentTables } from '../api/client';
import PDFViewer from './PDFViewer';
import TableViewer from './TableViewer';

function formatKey(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function DocumentDetail({ uploadId, document: doc }) {
  const [activeTab, setActiveTab] = useState('pages');
  const [tables, setTables] = useState([]);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tablesError, setTablesError] = useState(null);

  // Reset tab when document changes
  useEffect(() => {
    setActiveTab('pages');
  }, [doc.doc_instance_id]);

  // Load tables when tables tab is selected
  useEffect(() => {
    if (activeTab !== 'tables') return;
    setTablesLoading(true);
    setTablesError(null);
    getDocumentTables(uploadId, doc.doc_instance_id)
      .then((data) => setTables(data.tables || []))
      .catch((err) => setTablesError(err.message))
      .finally(() => setTablesLoading(false));
  }, [activeTab, uploadId, doc.doc_instance_id]);

  const pdfUrl = getDocumentPdfUrl(uploadId, doc.doc_instance_id);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-slate-800/60 bg-slate-950/40 px-6 py-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-slate-100">
                {formatKey(doc.key)}
              </h3>
              <span className="rounded-md bg-slate-700/50 px-2 py-0.5 text-xs font-mono text-slate-400">
                #{doc.instance_ordinal}
              </span>
              {doc.verifier_flagged && (
                <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-500">
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                  </svg>
                  Flagged
                </span>
              )}
            </div>
            <div className="mt-1.5 flex items-center gap-4 text-xs text-slate-500">
              <span>Pages {doc.start_page}–{doc.end_page} ({doc.page_count} page{doc.page_count !== 1 ? 's' : ''})</span>
              <span className="text-slate-700">·</span>
              <span>Section: {doc.section}</span>
              {doc.distinguishing_attribute && (
                <>
                  <span className="text-slate-700">·</span>
                  <span>{doc.distinguishing_attribute}</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1 text-xs text-slate-600">
            <span className="font-mono">{doc.doc_instance_id}</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-4 flex gap-1">
          <button
            onClick={() => setActiveTab('pages')}
            className={`rounded-lg px-4 py-1.5 text-xs font-medium transition-all ${
              activeTab === 'pages'
                ? 'bg-indigo-500/15 text-indigo-400'
                : 'text-slate-500 hover:bg-slate-800/50 hover:text-slate-300'
            }`}
          >
            Pages
          </button>
          <button
            onClick={() => setActiveTab('tables')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-medium transition-all ${
              activeTab === 'tables'
                ? 'bg-indigo-500/15 text-indigo-400'
                : 'text-slate-500 hover:bg-slate-800/50 hover:text-slate-300'
            }`}
          >
            Tables
            {doc.tables?.length > 0 && (
              <span className="rounded-full bg-slate-700/60 px-1.5 py-0.5 text-[10px]">
                {doc.tables.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'pages' && (
          <PDFViewer url={pdfUrl} key={doc.doc_instance_id} />
        )}
        {activeTab === 'tables' && (
          <div className="h-full overflow-y-auto px-6 py-4">
            {tablesLoading ? (
              <div className="flex items-center justify-center py-16">
                <svg className="h-6 w-6 animate-spin text-indigo-500" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                  <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                </svg>
              </div>
            ) : tablesError ? (
              <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
                {tablesError}
              </div>
            ) : tables.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <svg className="mb-3 h-10 w-10 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 0v1.5c0 .621-.504 1.125-1.125 1.125M12 18.375c0-.621.504-1.125 1.125-1.125" />
                </svg>
                <p className="text-sm font-medium text-slate-500">No tables detected</p>
                <p className="mt-1 text-xs text-slate-600">
                  No tabular data was found in this document instance.
                </p>
              </div>
            ) : (
              <div className="space-y-6 stagger-children">
                {tables.map((table) => (
                  <TableViewer key={table.table_id} table={table} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
