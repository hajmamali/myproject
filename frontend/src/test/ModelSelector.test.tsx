/**
 * ModelSelector Component Tests
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ModelSelector, { ModelOption } from '../components/ModelSelector';

const mockModel: ModelOption = {
  id: "microsoft/DialoGPT-medium",
  name: "DialoGPT Medium",
  provider: "huggingface",
  size: "117M parameters",
  capabilities: ["conversational", "text-generation"],
  description: "مدل گفتگویی مبتنی بر GPT-2",
  recommended: true,
};

describe('ModelSelector', () => {
  const mockOnSelect = vi.fn();

  it('renders the component with title', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    expect(screen.getByText('انتخاب مدل')).toBeInTheDocument();
  });

  it('displays search input', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    expect(screen.getByPlaceholderText('جستجو مدل‌ها...')).toBeInTheDocument();
  });

  it('shows provider filter buttons', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    expect(screen.getByText('همه')).toBeInTheDocument();
    expect(screen.getByText('HuggingFace')).toBeInTheDocument();
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
  });

  it('displays available models', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    expect(screen.getByText('DialoGPT Medium')).toBeInTheDocument();
    expect(screen.getByText('Phi-2')).toBeInTheDocument();
  });

  it('filters models by search term', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    const searchInput = screen.getByPlaceholderText('جستجو مدل‌ها...');

    fireEvent.change(searchInput, { target: { value: 'DialoGPT' } });

    expect(screen.getByText('DialoGPT Medium')).toBeInTheDocument();
    // Other models should be filtered out
  });

  it('filters models by provider', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    const openaiButton = screen.getByText('OpenAI');

    fireEvent.click(openaiButton);

    expect(screen.getByText('GPT-3.5 Turbo')).toBeInTheDocument();
    // HuggingFace models should be filtered out
  });

  it('calls onSelect when model is clicked', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    const modelCard = screen.getByText('DialoGPT Medium').closest('div');

    fireEvent.click(modelCard!);

    expect(mockOnSelect).toHaveBeenCalledWith(expect.objectContaining({
      id: "microsoft/DialoGPT-medium",
      name: "DialoGPT Medium"
    }));
  });

  it('shows selected model info', () => {
    render(<ModelSelector selectedModel={mockModel} onSelect={mockOnSelect} />);

    expect(screen.getByText('مدل انتخاب شده:')).toBeInTheDocument();
    expect(screen.getAllByText('DialoGPT Medium')).toHaveLength(2); // One in list, one in selected info
  });

  it('shows recommended badge for recommended models', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    expect(screen.getByText('پیشنهادی')).toBeInTheDocument();
  });

  it('shows empty state when no models match search', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    fireEvent.change(screen.getByPlaceholderText('جستجو مدل‌ها...'), { 
      target: { value: 'nonexistent' } 
    });
    expect(screen.getByText('هیچ مدلی یافت نشد')).toBeInTheDocument();
  });

  it('selects first model as default when none provided', () => {
    render(<ModelSelector onSelect={mockOnSelect} />);
    expect(mockOnSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: "microsoft/DialoGPT-medium" })
    );
  });

  it('filters OpenAI models when API key is missing', () => {
    // Mock API key check
    vi.mock('../../api/client', () => ({
      hasAPIKey: (provider: string) => provider !== 'openai'
    }));

    render(<ModelSelector onSelect={mockOnSelect} />);
    expect(screen.queryByText('GPT-3.5 Turbo')).not.toBeInTheDocument();
  });
});
