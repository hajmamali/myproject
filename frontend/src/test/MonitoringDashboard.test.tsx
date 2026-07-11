/**
 * MonitoringDashboard Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MonitoringDashboard from '../components/MonitoringDashboard';

// Mock the training client
vi.mock('../api/trainingClient', () => ({
  listTrainingJobs: vi.fn(),
  stopTrainingJob: vi.fn(),
  deleteTrainingJob: vi.fn(),
}));

import { listTrainingJobs, stopTrainingJob, deleteTrainingJob } from '../api/trainingClient';

const mockTrainingJobs = [
  {
    job_id: 'job_1',
    status: 'running' as const,
    config: {
      model_name: 'microsoft/DialoGPT-medium',
      training_mode: 'lora' as const,
      num_train_epochs: 3,
    },
    progress: {
      epoch: 1,
      step: 50,
      total_steps: 100,
      loss: 0.234,
      learning_rate: 0.0002,
    },
    created_at: '2025-12-29T10:00:00Z',
    started_at: '2025-12-29T10:05:00Z',
  },
  {
    job_id: 'job_2',
    status: 'completed' as const,
    config: {
      model_name: 'gpt-3.5-turbo',
      training_mode: 'full_finetune' as const,
      num_train_epochs: 5,
    },
    metrics: {
      train_loss: 0.123,
      accuracy: 0.89,
    },
    created_at: '2025-12-28T15:00:00Z',
    started_at: '2025-12-28T15:10:00Z',
    completed_at: '2025-12-29T08:00:00Z',
  },
];

describe('MonitoringDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (listTrainingJobs as any).mockResolvedValue({
      jobs: mockTrainingJobs,
      total: 2,
      limit: 20,
      offset: 0,
    });
    (stopTrainingJob as any).mockResolvedValue({ success: true, message: 'Stopped' });
    (deleteTrainingJob as any).mockResolvedValue({ success: true, message: 'Deleted' });
  });

  it('renders the component with title', () => {
    render(<MonitoringDashboard />);
    expect(screen.getByText('مانیتورینگ سیستم')).toBeInTheDocument();
  });

  it('displays system metrics', () => {
    render(<MonitoringDashboard />);
    expect(screen.getByText('CPU')).toBeInTheDocument();
    expect(screen.getByText('حافظه')).toBeInTheDocument();
    expect(screen.getByText('کارهای فعال')).toBeInTheDocument();
    expect(screen.getByText('Uptime')).toBeInTheDocument();
  });

  it('loads and displays training jobs', async () => {
    render(<MonitoringDashboard />);

    await waitFor(() => {
      expect(screen.getByText('microsoft/DialoGPT-medium')).toBeInTheDocument();
      expect(screen.getByText('gpt-3.5-turbo')).toBeInTheDocument();
    });

    expect(listTrainingJobs).toHaveBeenCalled();
  });

  it('displays job status correctly', async () => {
    render(<MonitoringDashboard />);

    await waitFor(() => {
      expect(screen.getByText('در حال اجرا')).toBeInTheDocument();
      expect(screen.getByText('تکمیل شده')).toBeInTheDocument();
    });
  });

  it('shows progress bar for running jobs', async () => {
    render(<MonitoringDashboard />);

    await waitFor(() => {
      expect(screen.getByText('پیشرفت: 50/100')).toBeInTheDocument();
      expect(screen.getByText('Epoch 1')).toBeInTheDocument();
    });
  });

  it('allows selecting a job to view details', async () => {
    render(<MonitoringDashboard />);

    await waitFor(() => {
      const jobCard = screen.getByText('microsoft/DialoGPT-medium').closest('div');
      fireEvent.click(jobCard!);
    });

    expect(screen.getByText('جزئیات کار')).toBeInTheDocument();
  });

  it('displays job details when selected', async () => {
    render(<MonitoringDashboard />);

    await waitFor(() => {
      const jobCard = screen.getByText('microsoft/DialoGPT-medium').closest('div');
      fireEvent.click(jobCard!);
    });

    expect(screen.getByText('microsoft/DialoGPT-medium')).toBeInTheDocument();
    expect(screen.getByText('lora')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // epochs
  });

  it('shows metrics for completed jobs', async () => {
    render(<MonitoringDashboard />);

    await waitFor(() => {
      const jobCard = screen.getByText('gpt-3.5-turbo').closest('div');
      fireEvent.click(jobCard!);
    });

    expect(screen.getByText('0.123')).toBeInTheDocument(); // train_loss
    expect(screen.getByText('89.0%')).toBeInTheDocument(); // accuracy
  });

  it('allows stopping running jobs', async () => {
    // Mock window.confirm
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<MonitoringDashboard />);

    await waitFor(() => {
      const stopButton = screen.getAllByTitle('توقف کار')[0];
      fireEvent.click(stopButton);
    });

    expect(confirmSpy).toHaveBeenCalledWith('آیا مطمئن هستید که می‌خواهید این کار را متوقف کنید؟');
    expect(stopTrainingJob).toHaveBeenCalledWith('job_1');

    confirmSpy.mockRestore();
  });

  it('allows deleting jobs', async () => {
    // Mock window.confirm
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<MonitoringDashboard />);

    await waitFor(() => {
      const deleteButton = screen.getAllByTitle('حذف کار')[0];
      fireEvent.click(deleteButton);
    });

    expect(confirmSpy).toHaveBeenCalledWith('آیا مطمئن هستید که می‌خواهید این کار را حذف کنید؟ این عمل قابل بازگشت نیست.');
    expect(deleteTrainingJob).toHaveBeenCalledWith('job_1');

    confirmSpy.mockRestore();
  });

  it('shows empty state when no job is selected', () => {
    render(<MonitoringDashboard />);
    expect(screen.getByText('یک کار را انتخاب کنید تا جزئیات آن نمایش داده شود')).toBeInTheDocument();
  });
});
