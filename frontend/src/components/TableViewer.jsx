import { useState, useMemo } from 'react';

export default function TableViewer({ table }) {
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');

  const handleSort = (colIndex) => {
    if (sortCol === colIndex) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortCol(colIndex);
      setSortDir('asc');
    }
  };

  const sortedRows = useMemo(() => {
    if (sortCol === null || !table.rows) return table.rows || [];
    const rows = [...table.rows];
    rows.sort((a, b) => {
      const valA = a[sortCol] ?? '';
      const valB = b[sortCol] ?? '';
      // Try numeric comparison
      const numA = parseFloat(valA);
      const numB = parseFloat(valB);
      if (!isNaN(numA) && !isNaN(numB)) {
        return sortDir === 'asc' ? numA - numB : numB - numA;
      }
      return sortDir === 'asc'
        ? valA.localeCompare(valB)
        : valB.localeCompare(valA);
    });
    return rows;
  }, [table.rows, sortCol, sortDir]);

  const headers = table.headers || [];

  return (
    <div className="rounded-xl border border-slate-800/60 bg-slate-800/20 backdrop-blur-sm overflow-hidden">
      {/* Table header */}
      <div className="flex items-center justify-between border-b border-slate-800/60 px-4 py-3">
        <div className="flex items-center gap-3">
          <h4 className="text-sm font-medium text-slate-200">
            {table.table_id}
          </h4>
          <span className="text-xs text-slate-500">
            pp. {table.page_range?.join('–')}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {table.spans_multiple_pages && (
            <span className="rounded-md bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-400">
              Multi-page
            </span>
          )}
          <span className="rounded-md bg-slate-700/50 px-2 py-0.5 text-[10px] font-medium text-slate-400">
            {table.extraction_method}
          </span>
          {table.verifier_flagged && (
            <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-500">
              <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              Flagged
            </span>
          )}
          <span className="text-[10px] text-slate-600">
            {table.row_count}×{table.col_count}
          </span>
        </div>
      </div>

      {/* Verifier notes */}
      {table.verifier_flagged && table.verifier_notes && (
        <div className="border-b border-amber-500/10 bg-amber-500/5 px-4 py-2">
          <p className="text-xs text-amber-400/80">{table.verifier_notes}</p>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        {headers.length === 0 && sortedRows.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-xs text-slate-600">Table has no data.</p>
          </div>
        ) : (
          <table className="w-full text-left text-xs">
            {headers.length > 0 && (
              <thead>
                <tr className="border-b border-slate-800/60">
                  {headers.map((header, i) => (
                    <th
                      key={i}
                      onClick={() => handleSort(i)}
                      className="cursor-pointer select-none whitespace-nowrap px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500 transition-colors hover:text-slate-300"
                    >
                      <div className="flex items-center gap-1">
                        {header}
                        {sortCol === i && (
                          <svg
                            className={`h-3 w-3 transition-transform ${
                              sortDir === 'desc' ? 'rotate-180' : ''
                            }`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth="2"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
                          </svg>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {sortedRows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className={`border-b border-slate-800/30 transition-colors hover:bg-slate-700/20 ${
                    rowIdx % 2 === 1 ? 'bg-slate-800/10' : ''
                  }`}
                >
                  {row.map((cell, cellIdx) => (
                    <td
                      key={cellIdx}
                      className="whitespace-nowrap px-4 py-2 text-slate-300"
                    >
                      {cell || <span className="text-slate-700">—</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
