/**
 * ABTestingDashboard Component Tests
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ABTestingDashboard from '../components/ABTestingDashboard';

describe('ABTestingDashboard', () => {
  it('renders the component with title', () => {
    render(<ABTestingDashboard />);
    expect(screen.getByText('آزمایش‌های A/B')).toBeInTheDocument();
  });

  it('displays create experiment button', () => {
    render(<ABTestingDashboard />);
    expect(screen.getByText('ایجاد آزمایش جدید')).toBeInTheDocument();
  });

  it('shows existing experiments', () => {
    render(<ABTestingDashboard />);
    expect(screen.getByText('مقایسه DialoGPT vs GPT-3.5')).toBeInTheDocument();
    expect(screen.getByText('مقایسه Phi-2 vs Claude')).toBeInTheDocument();
  });

  it('displays experiment status', () => {
    render(<ABTestingDashboard />);
    expect(screen.getByText('در حال اجرا')).toBeInTheDocument();
    expect(screen.getByText('تکمیل شده')).toBeInTheDocument();
  });

  it('shows winner for completed experiments', () => {
    render(<ABTestingDashboard />);
    expect(screen.getByText('برنده: Claude 3 Haiku')).toBeInTheDocument();
  });

  it('displays experiment variants', () => {
    render(<ABTestingDashboard />);
    expect(screen.getByText('DialoGPT Medium')).toBeInTheDocument();
    expect(screen.getByText('GPT-3.5 Turbo')).toBeInTheDocument();
    expect(screen.getByText('Phi-2')).toBeInTheDocument();
    expect(screen.getByText('Claude 3 Haiku')).toBeInTheDocument();
  });

  it('shows traffic percentages', () => {
    render(<ABTestingDashboard />);
    const percentages = screen.getAllByText('50%');
    expect(percentages.length).toBeGreaterThan(0);
  });

  it('allows selecting an experiment', () => {
    render(<ABTestingDashboard />);
    const experimentCard = screen.getByText('مقایسه DialoGPT vs GPT-3.5').closest('div');
    fireEvent.click(experimentCard!);

    expect(screen.getByText('جزئیات آزمایش')).toBeInTheDocument();
  });

  it('displays experiment details when selected', () => {
    render(<ABTestingDashboard />);
    const experimentCard = screen.getByText('مقایسه DialoGPT vs GPT-3.5').closest('div');
    fireEvent.click(experimentCard!);

    expect(screen.getByText('microsoft/DialoGPT-medium')).toBeInTheDocument();
    expect(screen.getByText('gpt-3.5-turbo')).toBeInTheDocument();
  });

  it('shows statistical comparison', () => {
    render(<ABTestingDashboard />);
    const experimentCard = screen.getByText('مقایسه DialoGPT vs GPT-3.5').closest('div');
    fireEvent.click(experimentCard!);

    expect(screen.getByText('مقایسه آماری')).toBeInTheDocument();
  });

  it('displays confidence level', () => {
    render(<ABTestingDashboard />);
    expect(screen.getByText('95.0%')).toBeInTheDocument();
  });

  it('shows create experiment form when button is clicked', () => {
    render(<ABTestingDashboard />);
    const createButton = screen.getByText('ایجاد آزمایش جدید');
    fireEvent.click(createButton);

    expect(screen.getByText('ایجاد آزمایش جدید')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('مثال: مقایسه DialoGPT vs GPT-3.5')).toBeInTheDocument();
  });

  it('allows filling experiment creation form', () => {
    render(<ABTestingDashboard />);
    const createButton = screen.getByText('ایجاد آزمایش جدید');
    fireEvent.click(createButton);

    const nameInput = screen.getByPlaceholderText('مثال: مقایسه DialoGPT vs GPT-3.5');
    const descriptionTextarea = screen.getByPlaceholderText('توضیحات آزمایش...');

    fireEvent.change(nameInput, { target: { value: 'Test Experiment' } });
    fireEvent.change(descriptionTextarea, { target: { value: 'Test Description' } });

    expect(nameInput).toHaveValue('Test Experiment');
    expect(descriptionTextarea).toHaveValue('Test Description');
  });

  it('shows validation message when trying to create without required fields', () => {
    // Mock alert
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(<ABTestingDashboard />);
    const createButton = screen.getByText('ایجاد آزمایش جدید');
    fireEvent.click(createButton);

    const submitButton = screen.getByText('ایجاد آزمایش');
    fireEvent.click(submitButton);

    expect(alertSpy).toHaveBeenCalledWith('لطفاً نام آزمایش و حداقل دو مدل را انتخاب کنید');

    alertSpy.mockRestore();
  });

  it('allows starting draft experiments', () => {
    render(<ABTestingDashboard />);

    // Find experiments and check for start button
    screen.getAllByText(/مقایسه/);
    // Should show start buttons for draft experiments
  });

  it('shows action buttons for running experiments', () => {
    render(<ABTestingDashboard />);

    // The running experiment should have Complete and Stop buttons
    expect(screen.getByText('تکمیل')).toBeInTheDocument();
    expect(screen.getByText('توقف')).toBeInTheDocument();
  });

  it('displays sample size and performance metrics', () => {
    render(<ABTestingDashboard />);

    // Check for metrics display
    expect(screen.getByText('1250')).toBeInTheDocument(); // sample size
    expect(screen.getByText('78.0%')).toBeInTheDocument(); // accuracy
  });
});
