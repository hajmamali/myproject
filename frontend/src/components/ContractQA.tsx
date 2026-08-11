/**
 * Contract QA Component
 */

import { useState } from 'react';

export default function ContractQA() {
  const [question, setQuestion] = useState('');
  const [answer] = useState('');

  const handleAsk = () => {
    // Handle question submission
    console.log('Question:', question);
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Contract Q&A</h1>
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Ask about a contract</label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Enter your question..."
            rows={4}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          onClick={handleAsk}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Get Answer
        </button>
        {answer && <div className="mt-4 p-4 bg-slate-50 rounded-lg text-slate-900">{answer}</div>}
      </div>
    </div>
  );
}
