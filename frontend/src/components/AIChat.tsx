/**
 * AI Chat Interface - Harvey-Style
 * 
 * Features:
 * - Streaming responses
 * - Markdown rendering
 * - Citation cards
 * - Confidence indicators
 * - Copy to clipboard
 * - Export conversation
 */

import { useState, useRef, useEffect } from "react";
import { 
  PaperAirplaneIcon, 
  DocumentDuplicateIcon,
  CheckIcon,
  SparklesIcon
} from "@heroicons/react/24/outline";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  confidence?: number;
  citations?: Array<{
    text: string;
    source: string;
  }>;
  isStreaming?: boolean;
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "سلام! من دستیار هوش مصنوعی حقوقی ماحون هستم. چطور می‌تونم کمکتون کنم؟",
      timestamp: new Date(),
      confidence: 1.0,
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Simulate streaming response (replace with actual API call)
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, assistantMessage]);

    // Simulate streaming
    const response = "بر اساس ماده ۲۱۹ قانون آیین دادرسی مدنی، دادگاه می‌تواند در صورت تشخیص، به طرفین مهلت مناسبی برای تقدیم دلایل و مدارک بدهد.";
    let currentText = "";
    
    for (let i = 0; i < response.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 20));
      currentText += response[i];
      
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessage.id
            ? { ...msg, content: currentText }
            : msg
        )
      );
    }

    // Finalize message with confidence and citations
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantMessage.id
          ? {
              ...msg,
              isStreaming: false,
              confidence: 0.95,
              citations: [
                { text: "ماده ۲۱۹ ق.آ.د.م", source: "قانون آیین دادرسی مدنی" },
              ],
            }
          : msg
      )
    );

    setIsLoading(false);
  };

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
            <SparklesIcon className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-100">ماحون AI</h1>
            <p className="text-sm text-slate-500">دستیار هوش مصنوعی حقوقی</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-4 ${message.role === "user" ? "flex-row-reverse" : ""}`}
          >
            {/* Avatar */}
            <div
              className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                message.role === "user"
                  ? "bg-slate-700"
                  : "bg-gradient-to-br from-blue-500 to-purple-500"
              }`}
            >
              {message.role === "user" ? (
                <span className="text-white font-medium">شما</span>
              ) : (
                <SparklesIcon className="h-5 w-5 text-white" />
              )}
            </div>

            {/* Message Content */}
            <div className={`flex-1 ${message.role === "user" ? "text-right" : ""}`}>
              <div
                className={`inline-block max-w-3xl rounded-2xl px-6 py-4 ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-800/50 text-slate-100 border border-slate-700"
                }`}
              >
                <div className="whitespace-pre-wrap leading-relaxed">
                  {message.content}
                  {message.isStreaming && (
                    <span className="inline-block w-1 h-5 bg-current ml-1 animate-pulse" />
                  )}
                </div>

                {/* Confidence Badge */}
                {message.confidence && message.role === "assistant" && (
                  <div className="mt-3 flex items-center gap-2 text-sm text-slate-400">
                    <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500"
                        style={{ width: `${message.confidence * 100}%` }}
                      />
                    </div>
                    <span>{Math.round(message.confidence * 100)}% اطمینان</span>
                  </div>
                )}

                {/* Citations */}
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {message.citations.map((citation, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 p-3 bg-slate-900/50 rounded-lg border border-slate-700"
                      >
                        <DocumentDuplicateIcon className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-blue-400">
                            {citation.text}
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5">
                            {citation.source}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Actions */}
              {message.role === "assistant" && !message.isStreaming && (
                <div className="mt-2 flex items-center gap-2">
                  <button
                    onClick={() => handleCopy(message.content, message.id)}
                    className="p-1.5 text-slate-500 hover:text-slate-300 hover:bg-slate-800 rounded transition-colors"
                    title="کپی"
                  >
                    {copiedId === message.id ? (
                      <CheckIcon className="h-4 w-4 text-green-500" />
                    ) : (
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-slate-800 bg-slate-900/50 backdrop-blur-sm p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3 bg-slate-800 rounded-2xl border border-slate-700 focus-within:border-blue-500 transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="سؤال خود را بپرسید..."
              disabled={isLoading}
              rows={1}
              className="flex-1 bg-transparent border-none outline-none text-slate-100 placeholder-slate-500 px-6 py-4 resize-none max-h-32"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="flex-shrink-0 m-2 p-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl transition-colors"
            >
              <PaperAirplaneIcon className="h-5 w-5" />
            </button>
          </div>
          <div className="mt-2 text-xs text-slate-500 text-center">
            برای ارسال Enter و برای خط جدید Shift+Enter را فشار دهید
          </div>
        </div>
      </div>
    </div>
  );
}
