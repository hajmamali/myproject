import { useState } from "react";
import { 
  ShareIcon, 
  ArrowPathIcon, 
  CircleStackIcon, 
  MagnifyingGlassIcon,
  ChevronRightIcon,
  ClockIcon,
  SparklesIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  details?: string;
  confidence?: number;
}


export default function KnowledgeGraphCenter() {
  const [activeTab, setActiveTab] = useState<"builder" | "explorer" | "metrics">("explorer");

  // Mock Graph Data for the Explorer
  const [nodes] = useState<GraphNode[]>([
    { id: "1", label: "ماده ۱۲ قانون مدنی", type: "rule", details: "اموال غیرمنقول ذاتا یا به واسطه عمل انسان...", confidence: 0.98 },
    { id: "2", label: "قرارداد پیمانکاری آریا", type: "document", details: "قرارداد شماره ۹۸/۱۲/الف مورخ ۱۳۹۸/۱۲/۱۵", confidence: 0.95 },
    { id: "3", label: "تاخیر در تادیه", type: "concept", details: "عدم انجام تعهد در موعد مقرر موجب خسارت...", confidence: 0.92 },
    { id: "4", label: "رای وحدت رویه شماره ۷۴۴", type: "precedent", details: "مبدا محاسبه خسارت تاخیر تادیه از تاریخ مطالبه...", confidence: 0.97 },
  ]);

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Filtered nodes based on search
  const filteredNodes = searchQuery 
    ? nodes.filter(n => n.label.includes(searchQuery) || n.type.includes(searchQuery))
    : nodes;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-800 pb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-l from-indigo-400 to-cyan-400 bg-clip-text text-transparent flex items-center gap-2">
            <ShareIcon className="h-6 w-6 text-indigo-400" />
            Knowledge Graph Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">مدیریت، اکتشاف تعاملی و مانیتورینگ متریک‌های گراف دانش حقوقی</p>
        </div>

        {/* Tab Controls */}
        <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-0.5 self-start">
          {[
            { id: "explorer", label: "Graph Explorer" },
            { id: "builder", label: "Graph Builder" },
            { id: "metrics", label: "Metrics & Status" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all ${
                activeTab === tab.id
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Contents */}
      {activeTab === "explorer" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
          {/* Controls & Search Sidebar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col space-y-4">
            <div>
              <h2 className="text-sm font-bold text-white mb-2">اکتشاف گراف (Explorer)</h2>
              <p className="text-[11px] text-slate-400">جستجو در گره‌ها، بررسی وابستگی‌ها و پیگیری منشا مستندات حقوقی.</p>
            </div>

            {/* Search Input */}
            <div className="relative">
              <input
                type="text"
                placeholder="جستجو در گراف..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 pl-8 text-xs focus:outline-none focus:border-indigo-500 font-medium"
              />
              <MagnifyingGlassIcon className="h-4 w-4 text-slate-500 absolute left-2.5 top-2.5" />
            </div>

            {/* Entity List */}
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
              {filteredNodes.map((node) => (
                <button
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className={`w-full text-right p-3 rounded-lg border transition-all flex items-center justify-between text-xs cursor-pointer ${
                    selectedNode?.id === node.id
                      ? "bg-indigo-950/40 border-indigo-500/60 text-indigo-300"
                      : "bg-slate-950/60 border-slate-800/80 hover:bg-slate-900 text-slate-300"
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="font-semibold">{node.label}</span>
                    <span className="text-[10px] text-slate-500 font-mono mt-0.5">{node.type.toUpperCase()}</span>
                  </div>
                  <ChevronRightIcon className="h-3.5 w-3.5 opacity-60" />
                </button>
              ))}
            </div>
          </div>

          {/* Graph Canvas Visual Area */}
          <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-5 relative overflow-hidden flex flex-col">
            <div className="absolute top-4 right-4 z-10 flex gap-2">
              <span className="text-[10px] bg-slate-950 border border-slate-800 text-slate-400 px-2.5 py-1 rounded-full font-semibold">
                امکان زوم با اسکرول فعال
              </span>
            </div>

            {/* Interactive Graph Mock SVG Canvas */}
            <div className="flex-1 bg-slate-950 border border-slate-900 rounded-lg relative flex items-center justify-center min-h-[300px]">
              <svg className="absolute inset-0 w-full h-full opacity-35" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                    <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#334155" strokeWidth="0.5"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />
              </svg>

              {/* Edge Render Lines */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <line x1="20%" y1="50%" x2="50%" y2="25%" stroke="#6366f1" strokeWidth="1.5" strokeDasharray="4 4" />
                <line x1="50%" y1="25%" x2="80%" y2="50%" stroke="#6366f1" strokeWidth="1.5" />
                <line x1="50%" y1="25%" x2="50%" y2="75%" stroke="#6366f1" strokeWidth="1.5" />
              </svg>

              {/* Interactive Node Anchors */}
              <div className="absolute left-[15%] top-[45%] flex flex-col items-center">
                <button 
                  onClick={() => setSelectedNode(nodes[1])}
                  className={`h-10 w-10 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-110 cursor-pointer ${
                    selectedNode?.id === "2" ? "bg-amber-600 ring-4 ring-amber-500/20 text-white" : "bg-slate-800 border border-slate-700 text-amber-400"
                  }`}
                >
                  <CircleStackIcon className="h-5 w-5" />
                </button>
                <span className="text-[10px] text-slate-400 mt-1.5 font-semibold bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">قرارداد آریا</span>
              </div>

              <div className="absolute left-[45%] top-[20%] flex flex-col items-center">
                <button 
                  onClick={() => setSelectedNode(nodes[2])}
                  className={`h-10 w-10 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-110 cursor-pointer ${
                    selectedNode?.id === "3" ? "bg-indigo-600 ring-4 ring-indigo-500/20 text-white" : "bg-slate-800 border border-slate-700 text-indigo-400"
                  }`}
                >
                  <SparklesIcon className="h-5 w-5" />
                </button>
                <span className="text-[10px] text-slate-400 mt-1.5 font-semibold bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">تاخیر تادیه</span>
              </div>

              <div className="absolute left-[75%] top-[45%] flex flex-col items-center">
                <button 
                  onClick={() => setSelectedNode(nodes[0])}
                  className={`h-10 w-10 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-110 cursor-pointer ${
                    selectedNode?.id === "1" ? "bg-emerald-600 ring-4 ring-emerald-500/20 text-white" : "bg-slate-800 border border-slate-700 text-emerald-400"
                  }`}
                >
                  <ShieldCheckIcon className="h-5 w-5" />
                </button>
                <span className="text-[10px] text-slate-400 mt-1.5 font-semibold bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">قانون مدنی</span>
              </div>

              <div className="absolute left-[45%] top-[70%] flex flex-col items-center">
                <button 
                  onClick={() => setSelectedNode(nodes[3])}
                  className={`h-10 w-10 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-110 cursor-pointer ${
                    selectedNode?.id === "4" ? "bg-cyan-600 ring-4 ring-cyan-500/20 text-white" : "bg-slate-800 border border-slate-700 text-cyan-400"
                  }`}
                >
                  <ClockIcon className="h-5 w-5" />
                </button>
                <span className="text-[10px] text-slate-400 mt-1.5 font-semibold bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">وحدت رویه</span>
              </div>
            </div>

            {/* Selected Node Details Box */}
            <div className="mt-4 p-4 bg-slate-900 border border-slate-800 rounded-lg min-h-[90px]">
              {selectedNode ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-indigo-400">{selectedNode.label}</h3>
                    <span className="text-[9px] bg-slate-850 px-2 py-0.5 rounded font-mono text-slate-400 border border-slate-850">
                      CONFIDENCE: {(selectedNode.confidence || 0) * 100}%
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 mt-1.5 leading-relaxed">{selectedNode.details || "توضیحاتی ثبت نشده است."}</p>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                  برای دیدن جزئیات روابط و قوانین، یکی از گره‌های گراف را انتخاب کنید.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "builder" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-bold text-white">تنظیمات استخراج هوشمند (Extraction Settings)</h2>
            <p className="text-xs text-slate-400">تنظیمات فرآیند یادگیری عمیق و انطباق نهادهای حقوقی با هستی‌شناسی (Ontology) سامانه.</p>

            <div className="space-y-4 pt-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-slate-300">استخراج خودکار اشخاص و نهادها (NER)</label>
                <input type="checkbox" defaultChecked className="h-4 w-4 accent-indigo-500" />
              </div>

              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-slate-300">استخراج روابط معنایی (Relationships)</label>
                <input type="checkbox" defaultChecked className="h-4 w-4 accent-indigo-500" />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300">حد آستانه اطمینان استخراج (Confidence Threshold)</span>
                  <span className="text-indigo-400 font-mono">85%</span>
                </div>
                <input type="range" min="50" max="100" defaultValue="85" className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500" />
              </div>

              <button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 rounded-lg text-xs transition-colors flex items-center justify-center gap-2 cursor-pointer mt-4">
                <ArrowPathIcon className="h-4 w-4 animate-spin-hover" />
                <span>بروزرسانی هستی‌شناسی و استخراج مجدد</span>
              </button>
            </div>
          </div>

          {/* Data Sources Ingestion Status */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 flex flex-col justify-between">
            <div>
              <h2 className="text-sm font-bold text-white mb-2">منابع داده و اسناد فعال (Data Sources)</h2>
              <p className="text-xs text-slate-400">وضعیت پردازش اسناد آپلود شده در سیستم در راستای گراف دانش.</p>
            </div>

            <div className="space-y-2.5 my-4 flex-1 overflow-y-auto">
              {[
                { name: "آیین‌نامه اجرایی قانون ثبت اسناد.pdf", status: "completed", nodes: 24 },
                { name: "قرارداد پیمانکاری آریا آراد.pdf", status: "completed", nodes: 8 },
                { name: "لایحه دفاعیه شرکت تپسی.pdf", status: "processing", nodes: 0 },
              ].map((doc, idx) => (
                <div key={idx} className="bg-slate-950/60 border border-slate-850 p-3 rounded-lg flex items-center justify-between text-xs">
                  <div className="flex flex-col">
                    <span className="font-semibold text-slate-200">{doc.name}</span>
                    <span className="text-[10px] text-slate-500 font-medium mt-0.5">شامل {doc.nodes} گره معنایی</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    doc.status === "completed" ? "bg-green-950/40 text-green-400 border border-green-800/40" : "bg-indigo-950/40 text-indigo-400 border border-indigo-800/40 animate-pulse"
                  }`}>
                    {doc.status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "metrics" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">تعداد کل گره‌ها (Total Nodes)</h3>
            <p className="text-3xl font-extrabold text-white font-mono">۱,۴۸۲</p>
            <p className="text-[10px] text-slate-500 font-semibold">+۱۸ گره در ۲۴ ساعت گذشته</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">تعداد کل یال‌ها (Total Edges)</h3>
            <p className="text-3xl font-extrabold text-white font-mono">۴,۹۲۱</p>
            <p className="text-[10px] text-slate-500 font-semibold">ارتباط قانون‌گذاری و استناد</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">اطمینان استنتاج (RAG Grounding)</h3>
            <p className="text-3xl font-extrabold text-emerald-400 font-mono">۹۶.۴٪</p>
            <p className="text-[10px] text-emerald-500/80 font-semibold">بسیار مطلوب و مطابق قانون اساسی</p>
          </div>
        </div>
      )}
    </div>
  );
}
