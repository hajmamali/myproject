
/**
 * Model Selector Component
 *
 * Allows users to select from available AI models for fine-tuning and inference
 */

import { useState, useEffect, useMemo } from "react";
import { CpuChipIcon, MagnifyingGlassIcon, CheckCircleIcon } from "@heroicons/react/24/outline";
import { motion } from "framer-motion";

export interface ModelOption {
  id: string;
  name: string;
  provider: "huggingface" | "openai" | "anthropic" | "local";
  size: string;
  capabilities: string[];
  description: string;
  recommended?: boolean;
}

interface ModelSelectorProps {
  selectedModel?: ModelOption;
  onSelect: (model: ModelOption) => void;
  className?: string;
}

// Available GGUF models for MAHOUN platform
const AVAILABLE_MODELS: ModelOption[] = [
  {
    id: "unsloth/llama-3-8b-bnb-4bit",
    name: "Llama 3.2 (8B) - GGUF",
    provider: "local",
    size: "8B parameters",
    capabilities: ["text-generation", "reasoning", "legal", "gguf"],
    description: "مدل Llama 3.2 با کوانتیزاسیون 4-bit - مناسب برای استدلال حقوقی",
    recommended: true,
  },
  {
    id: "unsloth/llama-3-70b-bnb-4bit",
    name: "Llama 3.2 (70B) - GGUF",
    provider: "local",
    size: "70B parameters",
    capabilities: ["text-generation", "reasoning", "legal", "advanced", "gguf"],
    description: "مدل بزرگ Llama 3.2 - بهترین عملکرد برای تحلیل پیچیده حقوقی",
  },
  {
    id: "mistralai/mistral-7b-instruct-v0.3",
    name: "Mistral 7B Instruct - GGUF",
    provider: "local",
    size: "7B parameters",
    capabilities: ["text-generation", "reasoning", "instruction-following", "gguf"],
    description: "مدل Mistral با قابلیت دنبال کردن دستورات - سریع و دقیق",
    recommended: true,
  },
  {
    id: "mistralai/mixtral-8x7b-instruct-v0.1",
    name: "Mixtral 8x7B Instruct - GGUF",
    provider: "local",
    size: "8x7B parameters (MoE)",
    capabilities: ["text-generation", "reasoning", "advanced", "multilingual", "gguf"],
    description: "مدل Mixture-of-Experts قدرتمند - عملکرد عالی با کارایی بالا",
  },
  {
    id: "mistralai/mistral-nemo-instruct-2407",
    name: "Mistral Nemo 12B - GGUF",
    provider: "local",
    size: "12B parameters",
    capabilities: ["text-generation", "reasoning", "long-context", "gguf"],
    description: "مدل Mistral Nemo با context window بزرگ - مناسب اسناد طولانی",
  },
  {
    id: "qwen/qwen-2.5-coder-7b",
    name: "Qwen 2.5 Coder (7B) - GGUF",
    provider: "local",
    size: "7B parameters",
    capabilities: ["code-generation", "reasoning", "cypher", "gguf"],
    description: "مدل Qwen متخصص کدنویسی - برای تولید کوئری Cypher و کد",
  },
  {
    id: "qwen/qwen-2.5-14b",
    name: "Qwen 2.5 (14B) - GGUF",
    provider: "local",
    size: "14B parameters",
    capabilities: ["text-generation", "reasoning", "multilingual", "gguf"],
    description: "مدل چندمنظوره Qwen - پشتیبانی عالی از فارسی",
  },
  {
    id: "ibm/granite-3.0-8b-instruct",
    name: "Granite 3.0 Legal (8B) - GGUF",
    provider: "local",
    size: "8B parameters",
    capabilities: ["text-generation", "reasoning", "legal", "compliance", "gguf"],
    description: "مدل IBM Granite متخصص حقوق - آموزش دیده روی اسناد قانونی",
  },
  {
    id: "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    name: "Multilingual MPNet - Embedding",
    provider: "local",
    size: "278M parameters",
    capabilities: ["embeddings", "multilingual", "semantic-search"],
    description: "مدل embedding چندزبانه برای جستجوی معنایی - پشتیبانی از فارسی",
  },
];

export default function ModelSelector({ selectedModel, onSelect, className = "" }: ModelSelectorProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<string>("all");
  const [selectedCapability, setSelectedCapability] = useState<string>("all");
  const [filteredModels, setFilteredModels] = useState<ModelOption[]>([]);

  // All models are local GGUF models
  const getAvailableModels = useMemo(() => {
    return AVAILABLE_MODELS;
  }, []);

  // Set default model on first render
  useEffect(() => {
    const defaultModel = getAvailableModels[0];
    if (!selectedModel && defaultModel) {
      onSelect(defaultModel);
    }
  }, []);

  // Filter models based on search and provider
  useEffect(() => {
    let filtered = AVAILABLE_MODELS;

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(
        (model) =>
          model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          model.description.includes(searchTerm) ||
          model.capabilities.some((cap) => cap.includes(searchTerm))
      );
    }

    // Filter by provider
    if (selectedProvider !== "all") {
      filtered = filtered.filter((model) => model.provider === selectedProvider);
    }

    // Filter by capability
    if (selectedCapability !== "all") {
      filtered = filtered.filter((model) => 
        model.capabilities.includes(selectedCapability)
      );
    }

    setFilteredModels(filtered.length > 0 ? filtered : getAvailableModels);
  }, [searchTerm, selectedProvider]);

  const providers = [
    { id: "all", name: "همه", color: "bg-slate-700 text-slate-100" },
    { id: "local", name: "GGUF Local", color: "bg-primary-700 text-white" },
  ];

  const allCapabilities = useMemo(() => {
    const caps = new Set<string>();
    AVAILABLE_MODELS.forEach(model => {
      model.capabilities.forEach(cap => caps.add(cap));
    });
    return Array.from(caps);
  }, []);

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-lg ring-1 ring-gray-100/50 dark:ring-gray-700/50 ${className}`}>
      {/* Header */}
      <div className="p-6 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-700 dark:to-gray-800 border-b dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4 hover:[&>svg]:rotate-12 transition-transform">
          <CpuChipIcon className="h-7 w-7 text-blue-600 transition-transform" />
          <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">
            انتخاب مدل هوش مصنوعی
          </h2>
        </div>

        {/* Search */}
        <div className="relative">
          <MagnifyingGlassIcon className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="جستجو مدل‌ها..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-4 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Provider Filter */}
        <div className="flex flex-wrap gap-3 mt-4">
          {providers.map((provider) => (
            <button
              key={provider.id}
              onClick={() => setSelectedProvider(provider.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 hover:scale-105 ${
                selectedProvider === provider.id
                  ? "bg-gradient-to-br from-blue-600 to-purple-600 text-white shadow-md"
                  : `${provider.color} hover:shadow-sm`
              }`}
            >
              {provider.name}
            </button>
          ))}
        </div>
        </div>

        {/* Capability Filter */}
        <div className="flex flex-wrap gap-3 mt-4">
          <button
            onClick={() => setSelectedCapability("all")}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
              selectedCapability === "all"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-800 hover:bg-gray-200"
            }`}
          >
            همه قابلیت‌ها
          </button>
          {allCapabilities.map((capability) => (
            <button
              key={capability}
              onClick={() => setSelectedCapability(capability)}
              className={`px-4 py-2 rounded-full text-sm font-medium capitalize transition-all duration-300 ${
                selectedCapability === capability
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-800 hover:bg-gray-200"
              }`}
            >
              {capability}
            </button>
          ))}
        </div>

        {/* Models List */}
      <div className="max-h-[500px] overflow-y-auto p-2">
        {filteredModels.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            هیچ مدلی یافت نشد
          </div>
        ) : (
          <div className="space-y-3">
            {filteredModels.map((model, index) => (
                <motion.div
                  key={model.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`p-4 mb-2 rounded-lg transition-all duration-300 hover:shadow-md hover:scale-[1.02] ${
                    selectedModel?.id === model.id
                      ? "ring-2 ring-blue-500 bg-blue-50"
                      : "bg-white hover:bg-gray-50"
                  }`}
                  onClick={() => onSelect(model)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-900 dark:text-white">{model.name}</h3>
                        {model.recommended && (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                            پیشنهادی
                          </span>
                        )}
                        {selectedModel?.id === model.id && (
                          <CheckCircleIcon className="h-5 w-5 text-blue-600" />
                        )}
                      </div>

                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{model.description}</p>

                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
                          {model.size}
                        </span>
                        <span className="capitalize">{model.provider}</span>
                      </div>

                      <div className="flex flex-wrap gap-1 mt-2">
                        {model.capabilities.map((capability: string) => (
                          <span
                            key={capability}
                            className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded"
                          >
                            {capability}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Selected Model Info */}
      {selectedModel && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 border-t border-blue-200">
          <div className="flex items-center gap-2 text-sm font-medium text-blue-800">
            <CheckCircleIcon className="h-5 w-5" />
            <span>مدل انتخاب شده:</span>
            <span>{selectedModel.name}</span>
            <span className="text-blue-600">({selectedModel.id})</span>
          </div>
        </motion.div>
      )}
    </div>
  );
}
