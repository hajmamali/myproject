/**
 * Dataset Uploader Component
 * Upload documents and convert them to training datasets
 */

import { useState, useRef } from 'react';

interface DatasetInfo {
  dataset_id: string;
  doc_id: string;
  name: string;
  description: string;
  total_examples: number;
  train_examples: number;
  eval_examples: number;
  test_examples: number;
  avg_quality_score: number;
  total_qa_pairs: number;
  filtered_qa_pairs: number;
  grounded_qa_pairs: number;
  avg_groundedness_score: number;
  easy_count: number;
  medium_count: number;
  hard_count: number;
  dataset_path: string;
  created_at: string;
  processing_time_ms: number;
  success: boolean;
  error?: string;
  warnings: string[];
}

export default function DatasetUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<DatasetInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [domain, setDomain] = useState<'GENERAL' | 'LEGAL' | 'MEDICAL' | 'FINANCIAL'>('LEGAL');
  const [qaStrategy, setQaStrategy] = useState<'LLM' | 'TEMPLATE' | 'EXTRACTIVE' | 'HYBRID'>('HYBRID');
  const [minQualityScore, setMinQualityScore] = useState(0.7);
  const [enableGroundednessCheck, setEnableGroundednessCheck] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('domain', domain);
    formData.append('qa_strategy', qaStrategy);
    formData.append('min_quality_score', minQualityScore.toString());
    formData.append('enable_groundedness_check', enableGroundednessCheck.toString());
    formData.append('output_format', 'jsonl');

    try {
      // Use async endpoint for large files
      const response = await fetch('/api/v1/training-datasets/from-document/async', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const jobData = await response.json();
      const jobId = jobData.job_id;

      // Poll for job status
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/v1/training-datasets/jobs/${jobId}`);
          const statusData = await statusResponse.json();

          setProgress(statusData.progress * 100);

          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            setResult(statusData.result);
            setUploading(false);
          } else if (statusData.status === 'failed') {
            clearInterval(pollInterval);
            setError(statusData.error || 'Processing failed');
            setUploading(false);
          }
        } catch (e) {
          clearInterval(pollInterval);
          setError('Failed to check job status');
          setUploading(false);
        }
      }, 1000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setUploading(false);
    }
  };

  const getDifficultyColor = (count: number, total: number) => {
    const percentage = (count / total) * 100;
    if (percentage > 40) return 'text-red-400';
    if (percentage > 20) return 'text-yellow-400';
    return 'text-green-400';
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">ساخت دیتاست آموزشی</h1>
          <p className="text-slate-400">بارگذاری سند و تبدیل به دیتاست آموزشی با تولید Q&A</p>
        </div>

        {/* Upload Form */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-6">
          {/* File Selection */}
          <div className="mb-6">
            <label className="block text-slate-300 text-sm font-medium mb-2">
              انتخاب فایل (PDF, DOCX, TXT)
            </label>
            <div className="flex items-center gap-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors"
              >
                انتخاب فایل
              </button>
              {file && (
                <span className="text-slate-300">{file.name}</span>
              )}
            </div>
          </div>

          {/* Domain Selection */}
          <div className="mb-4">
            <label className="block text-slate-300 text-sm font-medium mb-2">
              دامنه سند
            </label>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value as any)}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white"
            >
              <option value="GENERAL">عمومی</option>
              <option value="LEGAL">حقوقی</option>
              <option value="MEDICAL">پزشکی</option>
              <option value="FINANCIAL">مالی</option>
            </select>
          </div>

          {/* Q&A Strategy */}
          <div className="mb-4">
            <label className="block text-slate-300 text-sm font-medium mb-2">
              استراتژی تولید Q&A
            </label>
            <select
              value={qaStrategy}
              onChange={(e) => setQaStrategy(e.target.value as any)}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white"
            >
              <option value="LLM">مدل زبانی (LLM)</option>
              <option value="TEMPLATE">قالب‌بندی</option>
              <option value="EXTRACTIVE">استخراجی</option>
              <option value="HYBRID">ترکیبی (Hybrid)</option>
            </select>
          </div>

          {/* Quality Settings */}
          <div className="mb-4">
            <label className="block text-slate-300 text-sm font-medium mb-2">
              حداقل امتیاز کیفیت: {minQualityScore.toFixed(2)}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={minQualityScore}
              onChange={(e) => setMinQualityScore(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Groundedness Check */}
          <div className="mb-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={enableGroundednessCheck}
                onChange={(e) => setEnableGroundednessCheck(e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-slate-300 text-sm">فعال‌سازی بررسی groundedness</span>
            </label>
          </div>

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg transition-colors"
          >
            {uploading ? 'در حال پردازش...' : 'شروع پردازش'}
          </button>

          {/* Progress */}
          {uploading && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-400 text-sm">پیشرفت</span>
                <span className="text-slate-300 text-sm">{progress.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div
                  className="bg-primary-600 h-2 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
              <p className="font-medium">خطا</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}
        </div>

        {/* Result */}
        {result && (
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-xl font-semibold text-white mb-4">نتیجه پردازش</h2>
            
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <div className="text-slate-400 text-sm mb-1">شناسه دیتاست</div>
                <div className="text-white font-mono text-sm">{result.dataset_id}</div>
              </div>
              <div>
                <div className="text-slate-400 text-sm mb-1">نام</div>
                <div className="text-white">{result.name}</div>
              </div>
              <div>
                <div className="text-slate-400 text-sm mb-1">کل مثال‌ها</div>
                <div className="text-white">{result.total_examples.toLocaleString('fa-IR')}</div>
              </div>
              <div>
                <div className="text-slate-400 text-sm mb-1">امتیاز کیفیت</div>
                <div className={`text-white font-bold ${
                  result.avg_quality_score >= 0.8 ? 'text-green-400' :
                  result.avg_quality_score >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {(result.avg_quality_score * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Splits */}
            <div className="mb-6">
              <h3 className="text-white font-medium mb-3">تقسیم داده‌ها</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-1">Train</div>
                  <div className="text-white font-bold">{result.train_examples}</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-1">Eval</div>
                  <div className="text-white font-bold">{result.eval_examples}</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-1">Test</div>
                  <div className="text-white font-bold">{result.test_examples}</div>
                </div>
              </div>
            </div>

            {/* Quality Metrics */}
            <div className="mb-6">
              <h3 className="text-white font-medium mb-3">معیارهای کیفیت</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-1">کل Q&A</div>
                  <div className="text-white">{result.total_qa_pairs}</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-1">فیلتر شده</div>
                  <div className="text-white">{result.filtered_qa_pairs}</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-1">Grounded</div>
                  <div className="text-white">{result.grounded_qa_pairs}</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-slate-400 text-xs mb-1">امتیاز Groundedness</div>
                  <div className="text-white">{(result.avg_groundedness_score * 100).toFixed(1)}%</div>
                </div>
              </div>
            </div>

            {/* Difficulty Distribution */}
            <div className="mb-6">
              <h3 className="text-white font-medium mb-3">توزیع سختی</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">آسان</span>
                  <span className={`font-medium ${getDifficultyColor(result.easy_count, result.total_examples)}`}>
                    {result.easy_count}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">متوسط</span>
                  <span className={`font-medium ${getDifficultyColor(result.medium_count, result.total_examples)}`}>
                    {result.medium_count}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">سخت</span>
                  <span className={`font-medium ${getDifficultyColor(result.hard_count, result.total_examples)}`}>
                    {result.hard_count}
                  </span>
                </div>
              </div>
            </div>

            {/* Warnings */}
            {result.warnings.length > 0 && (
              <div className="mb-6 bg-yellow-900/20 border border-yellow-800 rounded-lg p-4">
                <h3 className="text-yellow-400 font-medium mb-2">هشدارها</h3>
                <ul className="text-yellow-300 text-sm space-y-1">
                  {result.warnings.map((warning, index) => (
                    <li key={index}>• {warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Download Buttons */}
            <div className="flex gap-4">
              <button
                onClick={() => window.location.href = `/api/v1/training-datasets/${result.dataset_id}/download/train`}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                دانلود Train
              </button>
              <button
                onClick={() => window.location.href = `/api/v1/training-datasets/${result.dataset_id}/download/eval`}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                دانلود Eval
              </button>
              <button
                onClick={() => window.location.href = `/api/v1/training-datasets/${result.dataset_id}/download/test`}
                className="flex-1 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                دانلود Test
              </button>
            </div>
         </div>
        )}
      </div>
    </div>
  );
}
