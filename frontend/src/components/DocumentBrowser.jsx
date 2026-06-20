import { useState, useMemo } from 'react';

function formatKey(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function confidenceColor(confidence) {
  if (confidence >= 0.8) return 'bg-emerald-500';
  if (confidence >= 0.5) return 'bg-amber-500';
  return 'bg-rose-500';
}

export default function DocumentBrowser({ documents, selectedDoc, onSelectDoc }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedSections, setExpandedSections] = useState(new Set());

  // Group documents by key (doc type)
  const grouped = useMemo(() => {
    const map = new Map();
    for (const doc of documents) {
      if (!map.has(doc.key)) {
        map.set(doc.key, []);
      }
      map.get(doc.key).push(doc);
    }
    return map;
  }, [documents]);

  // Auto-expand all sections on first render
  useMemo(() => {
    setExpandedSections(new Set(grouped.keys()));
  }, [grouped]);

  // Filter documents by search query
  const filteredGrouped = useMemo(() => {
    if (!searchQuery.trim()) return grouped;
    const q = searchQuery.toLowerCase();
    const result = new Map();
    for (const [key, docs] of grouped) {
      const filtered = docs.filter(
        (d) =>
          d.key.toLowerCase().includes(q) ||
          d.section.toLowerCase().includes(q) ||
          d.doc_instance_id.toLowerCase().includes(q) ||
          d.distinguishing_attribute?.toLowerCase().includes(q)
      );
      if (filtered.length > 0) {
        result.set(key, filtered);
      }
    }
    return result;
  }, [grouped, searchQuery]);

  const toggleSection = (key) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="flex w-[300px] flex-shrink-0 flex-col border-r border-slate-800/60 bg-slate-950/40">
      {/* Search */}
      <div className="flex-shrink-0 border-b border-slate-800/60 p-3">
        <div className="relative">
          <svg className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter documents…"
            className="w-full rounded-lg border border-slate-800 bg-slate-900/50 py-1.5 pl-8 pr-3 text-xs text-slate-300 placeholder-slate-600 outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
          />
        </div>
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto py-1">
        {filteredGrouped.size === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-xs text-slate-600">No documents match your filter.</p>
          </div>
        ) : (
          Array.from(filteredGrouped.entries()).map(([key, docs]) => (
            <div key={key} className="mb-0.5">
              {/* Section header */}
              <button
                onClick={() => toggleSection(key)}
                className="flex w-full items-center justify-between px-4 py-2 text-left hover:bg-slate-800/40 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <svg
                    className={`h-3 w-3 text-slate-600 transition-transform ${
                      expandedSections.has(key) ? 'rotate-90' : ''
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    {formatKey(key)}
                  </span>
                </div>
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                  {docs.length}
                </span>
              </button>

              {/* Documents */}
              {expandedSections.has(key) && (
                <div className="pb-1">
                  {docs.map((doc) => {
                    const isSelected = selectedDoc?.doc_instance_id === doc.doc_instance_id;
                    return (
                      <button
                        key={doc.doc_instance_id}
                        onClick={() => onSelectDoc(doc)}
                        className={`group flex w-full items-center gap-3 px-4 py-2.5 pl-9 text-left transition-all ${
                          isSelected
                            ? 'bg-indigo-500/10 border-r-2 border-indigo-500'
                            : 'hover:bg-slate-800/40'
                        }`}
                      >
                        {/* Confidence dot */}
                        <div className={`h-2 w-2 flex-shrink-0 rounded-full ${confidenceColor(doc.boundary_confidence)}`} />

                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className={`truncate text-xs font-medium ${
                              isSelected ? 'text-indigo-400' : 'text-slate-300 group-hover:text-slate-200'
                            }`}>
                              {formatKey(doc.key)}
                            </span>
                            <span className="flex-shrink-0 rounded bg-slate-700/60 px-1.5 py-0.5 text-[10px] font-mono text-slate-400">
                              #{doc.instance_ordinal}
                            </span>
                            {doc.verifier_flagged && (
                              <svg className="h-3 w-3 flex-shrink-0 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                              </svg>
                            )}
                          </div>
                          <p className="mt-0.5 text-[10px] text-slate-600">
                            pp. {doc.start_page}–{doc.end_page}
                            {doc.distinguishing_attribute && ` · ${doc.distinguishing_attribute}`}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 border-t border-slate-800/60 px-4 py-2">
        <p className="text-[10px] text-slate-600">
          {documents.length} document{documents.length !== 1 ? 's' : ''} · {filteredGrouped.size} type{filteredGrouped.size !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
}
