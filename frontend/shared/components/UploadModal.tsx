import { useState } from 'react';

interface UploadModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function UploadModal({ isOpen, onClose }: UploadModalProps) {
    const [file, setFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setUploadStatus('idle');
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setIsUploading(true);
        setUploadStatus('idle');

        const formData = new FormData();
        formData.append('file', file);

        const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

        try {
            const response = await fetch(`${API_BASE_URL}/api/ingest/upload`, {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                setUploadStatus('success');
                setTimeout(() => {
                    onClose();
                    setFile(null);
                    setUploadStatus('idle');
                }, 2000);
            } else {
                const error = await response.json();
                setUploadStatus('error');
                setErrorMessage(error.detail || 'خطا در آپلود فایل');
            }
        } catch (error) {
            setUploadStatus('error');
            setErrorMessage('خطا در اتصال به سرور');
        } finally {
            setIsUploading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 rounded-2xl shadow-2xl max-w-lg w-full p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-slate-200">آپلود سند حقوقی</h2>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-slate-400 transition-colors"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="space-y-4">
                    <div className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center hover:border-primary-400 transition-colors">
                        <input
                            type="file"
                            id="file-upload"
                            className="hidden"
                            onChange={handleFileChange}
                            accept=".pdf,.doc,.docx,.txt"
                        />
                        <label htmlFor="file-upload" className="cursor-pointer">
                            <div className="flex flex-col items-center gap-2">
                                <svg className="w-12 h-12 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                </svg>
                                <p className="text-sm text-slate-400">
                                    {file ? file.name : 'فایل خود را انتخاب کنید'}
                                </p>
                                <p className="text-xs text-slate-400">PDF, DOC, DOCX, TXT</p>
                            </div>
                        </label>
                    </div>

                    {uploadStatus === 'success' && (
                        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
                            فایل با موفقیت آپلود شد
                        </div>
                    )}

                    {uploadStatus === 'error' && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                            {errorMessage}
                        </div>
                    )}

                    <div className="flex gap-3">
                        <button
                            onClick={handleUpload}
                            disabled={!file || isUploading}
                            className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-300 text-white font-medium rounded-lg transition-colors"
                        >
                            {isUploading ? 'در حال آپلود...' : 'آپلود'}
                        </button>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 border border-slate-600 hover:bg-slate-800 text-slate-300 font-medium rounded-lg transition-colors"
                        >
                            انصراف
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
