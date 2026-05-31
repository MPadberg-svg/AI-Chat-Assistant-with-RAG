export default function Sidebar({ documents, onDelete }) {
  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col bg-slate-900 p-4 text-white">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Uploaded documents
      </h3>
      {documents.length === 0 ? (
        <p className="text-sm text-slate-400">No documents uploaded yet.</p>
      ) : (
        <ul className="m-0 list-none p-0">
          {documents.map((docId) => (
            <li
              key={docId}
              className="flex items-center justify-between gap-2 border-b border-slate-800 py-2"
            >
              <span className="truncate text-sm text-slate-200">{docId}</span>
              <button
                onClick={() => onDelete(docId)}
                aria-label={`Delete ${docId}`}
                className="text-xs text-slate-500 transition-colors hover:text-red-400"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
