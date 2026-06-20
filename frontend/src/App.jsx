import { useState, useCallback } from 'react';
import './index.css';

import UploadView from './components/UploadView';
import ProcessingStatus from './components/ProcessingStatus';
import ResultsView from './components/ResultsView';

/**
 * View states:
 *  'upload'     — initial file selection
 *  'processing' — pipeline is running (SSE streaming)
 *  'results'    — processing complete, browsing documents
 */
export default function App() {
  const [view, setView] = useState('upload');
  const [currentUpload, setCurrentUpload] = useState(null); // { upload_id, filename, total_pages }
  const [fadeClass, setFadeClass] = useState('animate-fade-in');

  const transitionTo = useCallback((nextView) => {
    setFadeClass('opacity-0 transition-opacity duration-200');
    setTimeout(() => {
      setView(nextView);
      setFadeClass('animate-fade-in');
    }, 200);
  }, []);

  const handleUploadStarted = useCallback((uploadData) => {
    setCurrentUpload(uploadData);
    transitionTo('processing');
  }, [transitionTo]);

  const handleProcessingComplete = useCallback(() => {
    transitionTo('results');
  }, [transitionTo]);

  const handleBackToUpload = useCallback(() => {
    setCurrentUpload(null);
    transitionTo('upload');
  }, [transitionTo]);

  const handleViewResults = useCallback((uploadId) => {
    setCurrentUpload({ upload_id: uploadId });
    transitionTo('results');
  }, [transitionTo]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 font-sans">
      {/* Top bar */}
      <header className="sticky top-0 z-50 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-screen-2xl items-center justify-between px-6">
          <button
            onClick={handleBackToUpload}
            className="flex items-center gap-2.5 text-slate-100 hover:text-indigo-400 transition-colors"
          >
            <svg className="h-6 w-6 text-indigo-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12h.01M15 12h.01M12 3C7.03 3 3 7.03 3 12s4.03 9 9 9 9-4.03 9-9" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M21 3v6h-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="text-lg font-semibold tracking-tight">Infrragment</span>
          </button>

          <div className="flex items-center gap-4">
            {currentUpload && (
              <span className="text-xs font-medium text-slate-500">
                ID: {currentUpload.upload_id}
              </span>
            )}
            {view !== 'upload' && (
              <button
                onClick={handleBackToUpload}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-all"
              >
                New Upload
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className={`${fadeClass}`}>
        {view === 'upload' && (
          <UploadView
            onUploadStarted={handleUploadStarted}
            onViewResults={handleViewResults}
          />
        )}
        {view === 'processing' && currentUpload && (
          <ProcessingStatus
            uploadId={currentUpload.upload_id}
            filename={currentUpload.filename}
            totalPages={currentUpload.total_pages}
            onComplete={handleProcessingComplete}
          />
        )}
        {view === 'results' && currentUpload && (
          <ResultsView uploadId={currentUpload.upload_id} />
        )}
      </main>
    </div>
  );
}
