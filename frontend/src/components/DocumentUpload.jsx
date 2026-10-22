import { useRef, useState } from "react";

import { uploadDocument } from "../services/api";

const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".docx"];
const MAX_BYTES = 20 * 1024 * 1024;

export default function DocumentUpload({ onUploaded }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [toast, setToast] = useState(null);

  const handleFile = async (file) => {
    if (!file || isUploading) return;
    setToast(null);

    const suffix = `.${file.name.split(".").pop()?.toLowerCase() || ""}`;
    if (!ACCEPTED_EXTENSIONS.includes(suffix)) {
      setToast({ type: "error", text: "Only PDF, TXT and DOCX files are supported." });
      return;
    }
    if (file.size > MAX_BYTES) {
      setToast({ type: "error", text: "File is larger than the 20 MB limit." });
      return;
    }

    setIsUploading(true);
    setProgress(0);
    try {
      const result = await uploadDocument(file, (event) => {
        if (event.total) {
          setProgress(Math.round((event.loaded / event.total) * 100));
        }
      });
      setProgress(100);
      setToast({
        type: "success",
        text: result.duplicate
          ? `${file.name} is already in your library.`
          : `Indexed ${result.chunks} chunk${result.chunks === 1 ? "" : "s"} from ${file.name}.`,
      });
      await onUploaded?.(result);
    } catch (error) {
      setToast({
        type: "error",
        text: error?.response?.data?.detail || "Upload failed. Please try again.",
      });
    } finally {
      setIsUploading(false);
      setProgress(0);
      // Reset the input so selecting the same file again re-triggers onChange.
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const onDrop = async (event) => {
    event.preventDefault();
    setIsDragging(false);
    await handleFile(event.dataTransfer.files?.[0]);
  };

  const onFileChange = async (event) => {
    await handleFile(event.target.files?.[0]);
  };

  const dropZoneClasses = `border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
    isDragging
      ? "border-blue-500 bg-blue-50 text-blue-600"
      : "border-gray-300 text-gray-500"
  } ${isUploading ? "pointer-events-none opacity-60" : ""}`;

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a document"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        className={dropZoneClasses}
      >
        {isUploading
          ? "Uploading and indexing…"
          : "Drag and drop PDF/TXT/DOCX here, or click to upload"}
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
        <div
          className={`mt-2 text-sm ${toast.type === "error" ? "text-red-600" : "text-green-700"}`}
          role={toast.type === "error" ? "alert" : "status"}
        >
          {toast.type === "error" ? "⚠ " : "✓ "}
          {toast.text}
        </div>
      )}
    </div>
  );
}
