/**
 * Advanced Document Upload Component
 * 
 * Features:
 * - Drag & Drop
 * - Multiple file support
 * - Progress tracking
 * - Preview
 * - Metadata editing
 */

import { useState, useCallback, useRef } from "react";
import { 
  CloudArrowUpIcon, 
  DocumentIcon,
  XMarkIcon
} from "@heroicons/react/24/outline";
import { submitIngestionJob, submitDatasetGenerationJob, getDatasetJobStatus } from "../api/mahounClient";
import { toast } from "./Toast";
import JobStatusMonitor from "./JobStatusMonitor";

// Security constants
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const ALLOWED_FILE_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "image/jpeg",
  "image/png",
];

interface UploadedFile {
  file: File;
  id: string;
  status: "pending" | "submitting" | "submitted" | "error";
  jobId?: string;
  error?: string;
}

export default function AdvancedDocumentUpload() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadMode, setUploadMode] = useState<"ingestion" | "training">("ingestion");
  const [docType, setDocType] = useState("contract");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  }, []);

  const addFiles = (newFiles: File[]) => {
    // Security: Validate files
    const validFiles: File[] = [];
    const errors: string[] = [];

    for (const file of newFiles) {
      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: حجم فایل بیش از حد مجاز (حداکثر 50MB)`);
        continue;
      }

      // Check file type
      if (!ALLOWED_FILE_TYPES.includes(file.type)) {
        errors.push(`${file.name}: نوع فایل مجاز نیست`);
        continue;
      }

      validFiles.push(file);
    }

    // Show errors if any
    if (errors.length > 0) {
      errors.forEach((error) => toast.error(error));
    }

    // Process valid files only
    if (validFiles.length === 0) return;

    const uploadFiles: UploadedFile[] = validFiles.map(file => ({
      file,
      id: crypto.randomUUID(),
      status: "pending",
      uploadMode,
    }));

    setFiles(prev => [...prev, ...uploadFiles]);
    
    // Auto-upload
    uploadFiles.forEach(uploadFile => {
      if (uploadMode === "ingestion") {
        uploadFileAsync(uploadFile);
      } else {
        uploadDatasetAsync(uploadFile);
      }
    });
  };

  const uploadDatasetAsync = async (uploadFile: UploadedFile) => {
    setFiles(prev =>
      prev.map(f =>
        f.id === uploadFile.id ? { ...f, status: "submitting" } : f
      )
    );

    try {
      // Submit job
      const response = await submitDatasetGenerationJob(
        uploadFile.file,
        docType === "general_conditions" ? "general" : docType,
        "hybrid",
        0.7,
        true
      );

      setFiles(prev =>
        prev.map(f =>
          f.id === uploadFile.id
            ? { ...f, status: "submitted", jobId: response.job_id }
            : f
        )
      );
      
      toast.success(`فایل "${uploadFile.file.name}" برای استخراج دیتای آموزشی ارسال شد`);
      
      // Setup simple polling for this job since JobStatusMonitor handles ingestion jobs
      pollDatasetJob(uploadFile.id, response.job_id, uploadFile.file.name);
      
    } catch (error: any) {
      setFiles(prev =>
        prev.map(f =>
          f.id === uploadFile.id
            ? { ...f, status: "error", error: error.message }
            : f
        )
      );
      toast.error(`خطا در ارسال "${uploadFile.file.name}": ${error.message}`);
    }
  };
  
  const pollDatasetJob = async (fileId: string, jobId: string, fileName: string) => {
    const intervalId = setInterval(async () => {
      try {
        const status = await getDatasetJobStatus(jobId);
        
        if (status.status === "completed") {
          clearInterval(intervalId);
          toast.success(`دیتاست برای "${fileName}" با موفقیت ساخته شد!`);
          
          // Optionally download it or just let the user know
          const datasetInfo = status.result;
          if (datasetInfo) {
             toast.success(`${datasetInfo.total_examples} جفت Q&A استخراج شد.`);
          }
          
        } else if (status.status === "failed") {
          clearInterval(intervalId);
          toast.error(`خطا در ساخت دیتاست "${fileName}": ${status.error || "خطای نامشخص"}`);
          setFiles(prev =>
            prev.map(f =>
              f.id === fileId
                ? { ...f, status: "error", error: status.error || "خطای نامشخص" }
                : f
            )
          );
        }
      } catch (err) {
         console.error("Polling error", err);
      }
    }, 3000);
  };

  const uploadFileAsync = async (uploadFile: UploadedFile) => {
    setFiles(prev =>
      prev.map(f =>
        f.id === uploadFile.id ? { ...f, status: "submitting" } : f
      )
    );

    try {
      // Submit job (returns immediately with job_id)
      const response = await submitIngestionJob(
        uploadFile.file,
        docType,
        { uploaded_at: new Date().toISOString() }
      );

      setFiles(prev =>
        prev.map(f =>
          f.id === uploadFile.id
            ? { ...f, status: "submitted", jobId: response.job_id }
            : f
        )
      );
      
      toast.success(`فایل "${uploadFile.file.name}" برای پردازش ارسال شد`);
    } catch (error: any) {
      setFiles(prev =>
        prev.map(f =>
          f.id === uploadFile.id
            ? { ...f, status: "error", error: error.message }
            : f
        )
      );
      toast.error(`خطا در ارسال "${uploadFile.file.name}": ${error.message}`);
    }
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  return (
    <div className="max-w-4xl mx-auto p-6 page-enter">
      <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-700 p-8">
        <h2 className="text-2xl font-bold text-slate-100 mb-6">آپلود مدارک</h2>

        {/* Configuration Options */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Upload Mode Selector */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              حالت پردازش
            </label>
            <div className="flex bg-slate-800 rounded-lg p-1 border border-slate-700">
              <button
                className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                  uploadMode === "ingestion"
                    ? "bg-primary-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                onClick={() => setUploadMode("ingestion")}
              >
                تزریق به گراف (RAG)
              </button>
              <button
                className={`flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors ${
                  uploadMode === "training"
                    ? "bg-primary-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                onClick={() => setUploadMode("training")}
              >
                ساخت دیتاست آموزش
              </button>
            </div>
          </div>

          {/* Document Type Selector */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              نوع سند
            </label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full px-4 py-2 border border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-slate-900 text-slate-200"
            >
              <option value="contract">قرارداد</option>
              <option value="letter">نامه</option>
              <option value="report">گزارش</option>
              <option value="general_conditions">شرایط عمومی پیمان</option>
            </select>
          </div>
        </div>

        {/* Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`
            border-2 border-dashed rounded-xl p-12 text-center transition-colors
            ${isDragging 
              ? "border-primary-500 bg-primary-50" 
              : "border-slate-600 hover:border-slate-400"
            }
          `}
        >
          <CloudArrowUpIcon className="mx-auto h-12 w-12 text-slate-400 mb-4" />
          <p className="text-lg font-medium text-slate-300 mb-2">
            فایل‌ها را اینجا بکشید و رها کنید
          </p>
          <p className="text-sm text-slate-500 mb-4">
            یا برای انتخاب فایل کلیک کنید
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-6 py-2 bg-primary-700 text-white rounded-lg hover:bg-primary-800 transition-colors"
          >
            انتخاب فایل
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png"
          />
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-6 space-y-3">
            <h3 className="text-lg font-semibold text-slate-100 mb-3">
              فایل‌های آپلود شده ({files.length})
            </h3>
            {files.map((uploadFile) => (
              <div
                key={uploadFile.id}
                className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden"
              >
                {/* File Header */}
                <div className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3 flex-1">
                    <DocumentIcon className="h-8 w-8 text-slate-400" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-100 truncate">
                        {uploadFile.file.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {(uploadFile.file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      
                      {/* Status Indicators */}
                      {uploadFile.status === "submitting" && (
                        <p className="text-xs text-yellow-400 mt-1">
                          در حال ارسال...
                        </p>
                      )}
                      {(uploadFile as any).uploadMode === "training" && uploadFile.status === "submitted" && (
                        <p className="text-xs text-blue-400 mt-1">
                          در حال پردازش و استخراج Q&A (ممکن است زمان‌بر باشد)...
                        </p>
                      )}
                      {uploadFile.status === "error" && (
                        <p className="text-xs text-red-400 mt-1">{uploadFile.error}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(uploadFile.id)}
                    className="p-1 hover:bg-slate-700 rounded transition-colors"
                  >
                    <XMarkIcon className="h-5 w-5 text-slate-500" />
                  </button>
                </div>

                {/* Job Status Monitor (Only for Ingestion) */}
                {(uploadFile as any).uploadMode !== "training" && uploadFile.status === "submitted" && uploadFile.jobId && (
                  <div className="px-4 pb-4">
                    <JobStatusMonitor
                      jobId={uploadFile.jobId}
                      onComplete={() => {
                        toast.success(`پردازش "${uploadFile.file.name}" با موفقیت تکمیل شد`);
                      }}
                      onError={(error: string) => {
                        toast.error(`خطا در پردازش "${uploadFile.file.name}": ${error}`);
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
