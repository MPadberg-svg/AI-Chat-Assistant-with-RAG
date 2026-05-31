export default function SourceCitations({ sources }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {sources.map((source, index) => (
        <span
          key={`${source.doc_id}-${source.page}-${index}`}
          className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
        >
          {`${source.doc_id} · p.${source.page} · ${Math.round((source.score || 0) * 100)}%`}
        </span>
      ))}
    </div>
  );
}
