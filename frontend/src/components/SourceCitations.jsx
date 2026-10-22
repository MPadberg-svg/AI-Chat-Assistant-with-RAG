/** Convert a 0..1 similarity into a 0..100 percentage, clamped defensively. */
const toPercent = (score) => {
  const value = Number(score);
  if (!Number.isFinite(value)) return 0;
  return Math.round(Math.min(1, Math.max(0, value)) * 100);
};

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
          {`${source.filename || source.doc_id} · p.${source.page} · ${toPercent(source.score)}%`}
        </span>
      ))}
    </div>
  );
}
