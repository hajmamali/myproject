/**
 * Model Selector Component
 */

import { useState } from 'react';

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  version: string;
  description?: string;
}

interface ModelSelectorProps {
  onSelect?: (model: ModelOption) => void;
}

export default function ModelSelector({ onSelect }: ModelSelectorProps) {
  const [selectedModel, setSelectedModel] = useState<ModelOption | null>(null);

  const models: ModelOption[] = [
    {
      id: '1',
      name: 'GPT-4',
      provider: 'OpenAI',
      version: '4.0',
      description: 'Latest generation model',
    },
    {
      id: '2',
      name: 'Claude-3',
      provider: 'Anthropic',
      version: '3.0',
      description: 'Constitutional AI model',
    },
  ];

  const handleSelect = (model: ModelOption) => {
    setSelectedModel(model);
    onSelect?.(model);
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Select Model</h1>
      <div className="grid grid-cols-2 gap-4">
        {models.map((model) => (
          <button
            key={model.id}
            onClick={() => handleSelect(model)}
            className={`p-6 rounded-lg border-2 text-left transition ${
              selectedModel?.id === model.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="font-bold text-slate-900">{model.name}</div>
            <div className="text-sm text-slate-600">{model.provider}</div>
            {model.description && <div className="text-sm text-slate-500 mt-2">{model.description}</div>}
          </button>
        ))}
      </div>
    </div>
  );
}
