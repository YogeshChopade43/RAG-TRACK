import { useState, useRef, useCallback } from "react";
import { motion as Motion, AnimatePresence } from "framer-motion";
import "./PremiumFileUpload.css";

const PremiumFileUpload = ({ onFileSelect, isUploading, error }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [_dragCounter, setDragCounter] = useState(0);
  const fileInputRef = useRef(null);

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter((prev) => {
      const newCount = prev + 1;
      if (newCount > 0) setIsDragging(true);
      return newCount;
    });
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter((prev) => {
      const newCount = prev - 1;
      if (newCount === 0) setIsDragging(false);
      return newCount;
    });
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    setDragCounter(0);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  }, [onFileSelect]);

  const handleFileInput = useCallback((e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  }, [onFileSelect]);

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="upload-wrapper">
      <Motion.div
        className={`upload-dropzone ${isDragging ? "drag-active" : ""} ${error ? "has-error" : ""}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleBrowseClick}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInput}
          accept=".pdf,.txt,.doc,.docx,.md,.rtf"
          style={{ display: "none" }}
          disabled={isUploading}
          aria-label="Upload document file"
        />

        <div className="upload-icon-wrapper">
          <Motion.div
            className="upload-icon"
            animate={isDragging ? { scale: 1.1, rotate: 5 } : { scale: 1, rotate: 0 }}
            transition={{ duration: 0.3 }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </Motion.div>
        </div>

        <div className="upload-content">
          <AnimatePresence mode="wait">
            {isUploading ? (
              <Motion.div
                key="uploading"
                className="upload-state uploading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <div className="upload-spinner">
                  <div className="spinner-ring"></div>
                  <div className="spinner-ring"></div>
                </div>
                <p className="upload-message">Processing document...</p>
              </Motion.div>
            ) : isDragging ? (
              <Motion.div
                key="dragging"
                className="upload-state dragging"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
              >
                <p className="upload-message highlight">Release to upload</p>
                <p className="upload-subtext">Supported: PDF, TXT, DOC, DOCX, MD, RTF</p>
              </Motion.div>
            ) : (
              <Motion.div
                key="idle"
                className="upload-state idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <p className="upload-message">
                  <span>Drag & drop your document here</span>
                  <span className="upload-or">or</span>
                  <span className="upload-browse">browse files</span>
                </p>
                <p className="upload-subtext">Maximum file size: 50MB • Multiple formats supported</p>
              </Motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="upload-glow" aria-hidden="true"></div>
      </Motion.div>

      <AnimatePresence>
        {error && (
          <Motion.div
            className="upload-error"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            role="alert"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {error}
          </Motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PremiumFileUpload;
