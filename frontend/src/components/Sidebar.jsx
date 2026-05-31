export default function Sidebar({ documents, onDelete }) {
  return (
    <aside
      style={{
        width: "280px",
        borderRight: "1px solid #ddd",
        padding: "12px",
        background: "#fafafa",
      }}
    >
      <h3 style={{ marginTop: 0 }}>Uploaded documents</h3>
      {documents.length === 0 ? (
        <p style={{ color: "#666" }}>No documents uploaded yet.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {documents.map((docId) => (
            <li
              key={docId}
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "8px",
                alignItems: "center",
                padding: "6px 0",
              }}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{docId}</span>
              <button onClick={() => onDelete(docId)} aria-label={`Delete ${docId}`}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
