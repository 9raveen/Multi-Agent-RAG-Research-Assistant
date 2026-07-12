import { useState, useRef } from "react";
import { uploadPdf } from "../api";

export default function UploadPanel({ onUploadSuccess }) {
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setStatus("uploading");
    setError("");

    try {
      const data = await uploadPdf(file);
      setStatus("success");
      onUploadSuccess?.(data.filename);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setTimeout(() => setStatus("idle"), 3000);
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="upload-dropzone">
      <input
        type="file"
        accept="application/pdf"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
      <div className="upload-dropzone-content">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
        <span className="drop-title">Drop files here</span>
        <span className="drop-subtitle">PDF &middot; MD &middot; TXT &middot; DOCX</span>
        
        <button 
          className="browse-btn"
          onClick={handleButtonClick}
          disabled={status === "uploading"}
        >
          {status === "uploading" ? "UPLOADING..." : "BROWSE"}
        </button>
      </div>

      {status === "error" && (
        <div className="upload-error-msg">
          Failed: {error}
        </div>
      )}
      {status === "success" && (
        <div className="upload-success-msg">
          Document ingested!
        </div>
      )}
    </div>
  );
}

