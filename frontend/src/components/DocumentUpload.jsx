import { useRef, useState } from "react";

import { uploadDocument } from "../services/api";

export default function DocumentUpload({ onUploaded }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [toast, setToast] = useState("");

  const handleFile = async (file) => {
    setToast("");
    setProgress(0);
    try {
      const result = await uploadDocument(file, (event) => {
        if (event.total) {
          setProgress(Math.round((event.loaded / event.total) * 100));
        }
      });
      onUploaded(result.doc_id);
      setProgress(100);
    } catch (error) {
      setToast(error?.response?.data?.detail || "Upload failed. Please try again.");
    }
  };

  const onDrop = async (event) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) {
      await handleFile(file);
    }
  };

  const onFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      await handleFile(file);
    }
  };

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${isDragging ? "#4b73ff" : "#bbb"}`,
          borderRadius: "8px",
          padding: "20px",
          cursor: "pointer",
          textAlign: "center",
          background: isDragging ? "#f2f6ff" : "transparent",
        }}
      >
        Drag and drop PDF/TXT/DOCX here, or click to upload
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.docx"
        onChange={onFileChange}
        style={{ display: "none" }}
      />
      {progress > 0 && progress < 100 && (
        <div style={{ marginTop: "8px" }}>
          <div style={{ height: "8px", background: "#eee", borderRadius: "999px" }}>
            <div
              style={{
                width: `${progress}%`,
                height: "100%",
                background: "#4b73ff",
                borderRadius: "999px",
              }}
            />
          </div>
        </div>
      )}
      {toast && (
        <div style={{ marginTop: "8px", color: "#b00020", fontSize: "13px" }} role="alert">
          {toast}
        </div>
      )}
    </div>
  );
}
