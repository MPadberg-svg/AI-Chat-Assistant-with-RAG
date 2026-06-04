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

  const dropZoneClasses = `border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
    isDragging ? "border-blue-500 bg-blue-50 text-blue-600" : "border-gray-300 text-gray-500"
  }`;

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
        className={dropZoneClasses}
      >
        Drag and drop PDF/TXT/DOCX here, or click to upload
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.docx"
        onChange={onFileChange}
        className="hidden"
      />
      {progress > 0 && progress < 100 && (
        <div className="mt-2">
          <div className="h-2 rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
      {toast && (
        <div className="mt-2 text-sm text-red-600" role="alert">
          ⚠ {toast}
        </div>
      )}
    </div>
  );
}