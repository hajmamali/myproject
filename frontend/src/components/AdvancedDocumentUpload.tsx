/**
 * Advanced Document Upload Component
 */

import React, { useState } from 'react';

export default function AdvancedDocumentUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const newFiles = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setIsUploading(true);
    try {
      // Upload logic here
      console.log('Uploading files:', files);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Upload Documents</h1>
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-slate-300 rounded-lg p-12 text-center hover:border-blue-500 cursor-pointer"
      >
        <p className="text-slate-600 mb-2">Drag and drop files here</p>
        <p className="text-slate-500 text-sm">or click to browse</p>
      </div>
      {files.length > 0 && (
        <>
          <div className="mt-8 space-y-2">
            {files.map((file, i) => (
              <div key={i} className="flex items-center justify-between bg-slate-50 p-3 rounded">
                <span className="text-slate-900">{file.name}</span>
                <span className="text-slate-600 text-sm">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-400"
          >
            {isUploading ? 'Uploading...' : 'Upload Files'}
          </button>
        </>
      )}
    </div>
  );
}
