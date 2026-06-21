/**
 * Contract Q&A Interface
 * 
 * Advanced chat interface for contract questions with:
 * - Real-time answers
 * - Citation display
 * - Confidence scores
 * - History
 */

import { useState } from "react";
import { PaperAirplaneIcon, CheckCircleIcon } from "@heroicons/react/24/outline";
import { askContract, ContractQueryResponse } from "../api/mahounClient";

interface Message {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: Array<{
    doc_id: string;
    clause: string;
    citation_text: string;
  }>;
  confidence?: number;
  verified?: boolean;
}

export default function ContractQA() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [clauseNumber, setClauseNumber] = useState("");

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response: ContractQueryResponse = await askContract({
        query: input,
        clause_number: clauseNumber || undefined,
        top_k: 10,
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "assistant",
        content: response.answer,
        timestamp: new Date(),
        citations: response.citations,
        confidence: response.confidence,
        verified: response.verified,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "assistant",
        content: `خطا: ${error.message}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 h-screen flex flex-col page-enter">
      <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-700 flex flex-col h-full">
        {/* Header */}
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-2xl font-bold text-slate-100 mb-2">سؤال پیمانی</h2>
          <p className="text-sm text-slate-500">
            سؤالات خود درباره قراردادها را بپرسید
          </p>
          <div className="mt-4">
            <input
              type="text"
              value={clauseNumber}
              onChange={(e) => setClauseNumber(e.target.value)}
              placeholder="شماره بند خاص (اختیاری)"
              className="w-full md:w-auto px-4 py-2 border border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
            />
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 py-12">
              <p className="text-lg mb-2">خوش آمدید!</p>
              <p className="text-sm">سؤالات خود درباره قراردادها را بپرسید</p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${
                  message.type === "user"
                    ? "bg-primary-700 text-white"
                    : "bg-slate-800/80 text-slate-100"
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                
                {message.type === "assistant" && (
                  <div className="mt-3 space-y-2">
                    {message.verified && (
                      <div className="flex items-center gap-2 text-xs text-green-600">
                        <CheckCircleIcon className="h-4 w-4" />
                        تأیید شده
                      </div>
                    )}
                    {message.confidence !== undefined && (
                      <div className="text-xs text-slate-400">
                        اطمینان: {(message.confidence * 100).toFixed(0)}%
                      </div>
                    )}
                    {message.citations && message.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-600">
                        <p className="text-xs font-semibold mb-2">ارجاعات:</p>
                        <div className="space-y-1">
                          {message.citations.slice(0, 3).map((citation, idx) => (
                            <div key={idx} className="text-xs bg-slate-900 p-2 rounded border border-slate-700">
                              <p className="font-medium">{citation.citation_text}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-800/80 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-slate-600"></div>
                  <span className="text-sm text-slate-400">در حال پردازش...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="p-6 border-t border-slate-700">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSend()}
              placeholder="سؤال خود را بنویسید..."
              className="flex-1 px-4 py-3 border border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              disabled={loading}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-primary-700 text-white rounded-lg hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <PaperAirplaneIcon className="h-5 w-5" />
              ارسال
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
