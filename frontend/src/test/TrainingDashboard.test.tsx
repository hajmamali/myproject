/**
 * TrainingDashboard Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TrainingDashboard from '../components/TrainingDashboard';

describe('TrainingDashboard', () => {
  const mockOnStartTraining = vi.fn();

  it('renders the component with title', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);
    expect(screen.getByText('آموزش مدل')).toBeInTheDocument();
  });

  it('shows model selector', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);
    expect(screen.getByText('انتخاب مدل')).toBeInTheDocument();
  });

  it('displays training mode options', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);
    expect(screen.getByText('LoRA')).toBeInTheDocument();
    expect(screen.getByText('QLoRA')).toBeInTheDocument();
    expect(screen.getByText('Full Fine-tune')).toBeInTheDocument();
  });

  it('shows training parameters form', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);
    expect(screen.getByText('پارامترهای آموزش')).toBeInTheDocument();
    expect(screen.getByText('تعداد epochs')).toBeInTheDocument();
    expect(screen.getByText('Batch size (train)')).toBeInTheDocument();
    expect(screen.getByText('Learning rate')).toBeInTheDocument();
  });

  it('displays quantization options when QLoRA is selected', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);

    // Find and click QLoRA option
    const qloraOption = screen.getByText('QLoRA');
    fireEvent.click(qloraOption);

    expect(screen.getByText('Quantization')).toBeInTheDocument();
    expect(screen.getByText('INT8')).toBeInTheDocument();
    expect(screen.getByText('INT4')).toBeInTheDocument();
  });

  it('allows parameter input changes', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);

    const epochsInput = screen.getByDisplayValue('3'); // Default value
    fireEvent.change(epochsInput, { target: { value: '5' } });

    expect(epochsInput).toHaveValue(5);
  });

  it('shows start training button', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);
    expect(screen.getByText('شروع آموزش')).toBeInTheDocument();
  });

  it('disables start button when no model is selected', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);
    const startButton = screen.getByText('شروع آموزش');

    expect(startButton).toBeDisabled();
  });

  it('enables start button when model is selected', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);

    // First select a model
    const modelCard = screen.getByText('DialoGPT Medium').closest('div');
    fireEvent.click(modelCard!);

    const startButton = screen.getByText('شروع آموزش');
    expect(startButton).not.toBeDisabled();
  });

  it('shows loading state when training', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} isTraining={true} />);

    expect(screen.getByText('در حال آموزش...')).toBeInTheDocument();
  });

  it('calls onStartTraining when start button is clicked', async () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);

    // Select a model first
    const modelCard = screen.getByText('DialoGPT Medium').closest('div');
    fireEvent.click(modelCard!);

    // Click start training
    const startButton = screen.getByText('شروع آموزش');
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(mockOnStartTraining).toHaveBeenCalledWith(expect.objectContaining({
        model_name: "microsoft/DialoGPT-medium",
        training_mode: "lora",
        num_train_epochs: 3,
      }));
    });
  });

  it('shows dataset and output configuration', () => {
    render(<TrainingDashboard onStartTraining={mockOnStartTraining} />);
    expect(screen.getByText('داده‌ها و خروجی')).toBeInTheDocument();
    expect(screen.getByText('نام dataset')).toBeInTheDocument();
    expect(screen.getByText('نام run')).toBeInTheDocument();
  });
});
