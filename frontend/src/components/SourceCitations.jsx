export default function SourceCitations({ sources }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "8px" }}>
      {sources.map((source, index) => (
        <span
          key={`${source.doc_id}-${source.page}-${index}`}
          style={{
            display: "inline-block",
            background: "#e7efff",
            borderRadius: "999px",
            padding: "4px 10px",
            fontSize: "12px",
          }}
        >
          {`${source.doc_id} · p.${source.page} · ${Math.round((source.score || 0) * 100)}%`}
        </span>
      ))}
    </div>
  );
}
