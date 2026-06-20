import { useEffect, useRef, useState } from 'react';
import { streamStatus } from '../api/client';

const STAGES = [
  { key: 'uploading', label: 'Uploading' },
  { key: 'extracting_features', label: 'Extracting Features' },
  { key: 'detecting_boundaries', label: 'Detecting Boundaries' },
  { key: 'resolving_instances', label: 'Resolving Instances' },
  { key: 'verifying_boundaries', label: 'Verifying Boundaries' },
  { key: 'splitting_pdf', label: 'Splitting PDF' },
  { key: 'extracting_tables', label: 'Extracting Tables' },
  { key: 'verifying_tables', label: 'Verifying Tables' },
  { key: 'persisting', label: 'Persisting Results' },
  { key: 'completed', label: 'Complete' },
];

function getStageIndex(stageKey) {
  const idx = STAGES.findIndex((s) => s.key === stageKey);
  return idx === -1 ? 0 : idx;
}

export default function ProcessingStatus({ uploadId, filename, totalPages, onComplete }) {
  const [status, setStatus] = useState(null);
  const [failed, setFailed] = useState(false);
  const streamRef = useRef(null);

  useEffect(() => {
    if (!uploadId) return;

    streamRef.current = streamStatus(uploadId, (data) => {
      setStatus(data);
      if (data.stage === 'failed') {
        setFailed(true);
        streamRef.current?.close();
      }
      if (data.stage === 'completed') {
        streamRef.current?.close();
      }
    });

    return () => streamRef.current?.close();
  }, [uploadId]);

  const currentStageIndex = status ? getStageIndex(status.stage) : 0;
  const isComplete = status?.stage === 'completed';
  const progress = status?.progress ?? 0;

  return (
    <div className="mx-auto max-w-xl px-6 py-16 animate-slide-up">
      {/* Header */}
      <div className="mb-10 text-center">
        <h2 className="text-2xl font-bold tracking-tight text-slate-100">
          Processing Document
        </h2>
        {filename && (
          <p className="mt-2 text-sm text-slate-500">
            {filename}{totalPages ? ` · ${totalPages} pages` : ''}
          </p>
        )}
      </div>

      {/* Vertical stepper */}
      <div className="relative mx-auto max-w-md">
        {STAGES.map((stage, index) => {
          const isDone = index < currentStageIndex || isComplete;
          const isActive = index === currentStageIndex && !isComplete && !failed;
          const isFailed = failed && index === currentStageIndex;
          const isPending = index > currentStageIndex && !isComplete;

          return (
            <div key={stage.key} className="relative flex gap-4 pb-6 last:pb-0">
              {/* Vertical line */}
              {index < STAGES.length - 1 && (
                <div className="absolute left-[15px] top-[32px] w-[2px] h-[calc(100%-20px)]">
                  <div
                    className={`h-full w-full transition-colors duration-500 ${
                      isDone ? 'bg-indigo-500' : 'bg-slate-800'
                    }`}
                  />
                </div>
              )}

              {/* Icon */}
              <div className="relative z-10 flex-shrink-0">
                {isDone ? (
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/20 ring-2 ring-indigo-500">
                    <svg className="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </div>
                ) : isActive ? (
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/20 ring-2 ring-indigo-500">
                    <svg className="h-4 w-4 animate-spin text-indigo-400" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                      <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                    </svg>
                  </div>
                ) : isFailed ? (
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-rose-500/20 ring-2 ring-rose-500">
                    <svg className="h-4 w-4 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                ) : (
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 ring-2 ring-slate-700">
                    <div className="h-2 w-2 rounded-full bg-slate-600" />
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="flex-1 pt-1">
                <p className={`text-sm font-medium transition-colors ${
                  isDone ? 'text-slate-300' :
                  isActive ? 'text-slate-100' :
                  isFailed ? 'text-rose-400' :
                  'text-slate-600'
                }`}>
                  {stage.label}
                </p>

                {/* Show message for active stage */}
                {isActive && status?.message && (
                  <p className="mt-1 text-xs text-slate-500 animate-fade-in">
                    {status.message}
                  </p>
                )}

                {/* Progress bar for active stage */}
                {isActive && progress > 0 && (
                  <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-indigo-500 transition-all duration-500 ease-out"
                      style={{ width: `${Math.min(progress * 100, 100)}%` }}
                    />
                  </div>
                )}

                {/* Error message */}
                {isFailed && status?.error && (
                  <p className="mt-1 text-xs text-rose-400/80 animate-fade-in">
                    {status.error}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Actions */}
      {isComplete && (
        <div className="mt-10 flex justify-center animate-fade-in">
          <button
            onClick={onComplete}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-8 py-3 text-sm font-semibold text-white transition-all hover:bg-indigo-500 hover:shadow-lg hover:shadow-indigo-500/25 active:scale-[0.98]"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            View Results
          </button>
        </div>
      )}

      {failed && (
        <div className="mt-10 flex justify-center animate-fade-in">
          <p className="text-sm text-rose-400/80">
            Processing failed. Please try uploading again.
          </p>
        </div>
      )}
    </div>
  );
}
