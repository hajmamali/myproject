/**
 * Training API Client Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  startTrainingJob,
  getTrainingJobStatus,
  listTrainingJobs,
  getAvailableModels,
  getTrainingPresets
} from '../api/trainingClient';

// Mock fetch globally
const fetchMock = vi.fn();
// @ts-expect-error - mocking global fetch for tests
global.fetch = fetchMock;

describe('Training API Client', () => {
  beforeEach(() => {
    fetchMock.mockClear();
  });

  describe('startTrainingJob', () => {
    it('should start a training job successfully', async () => {
      const mockResponse = {
        success: true,
        job_id: 'job_123',
        message: 'Training started',
        job: { job_id: 'job_123', status: 'pending' }
      };

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const config = {
        model_name: 'test-model',
        training_mode: 'lora' as const,
        num_train_epochs: 3,
        per_device_train_batch_size: 4,
        per_device_eval_batch_size: 8,
        gradient_accumulation_steps: 4,
        learning_rate: 0.0002,
        weight_decay: 0.01,
        warmup_ratio: 0.03,
        max_grad_norm: 1.0
      };

      const result = await startTrainingJob(config);

      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/training/start',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(config)
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should throw error on API failure', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Invalid config' })
      });

      const config = {
        model_name: 'test-model',
        training_mode: 'lora' as const,
        num_train_epochs: 3,
        per_device_train_batch_size: 4,
        per_device_eval_batch_size: 8,
        gradient_accumulation_steps: 4,
        learning_rate: 0.0002,
        weight_decay: 0.01,
        warmup_ratio: 0.03,
        max_grad_norm: 1.0
      };

      await expect(startTrainingJob(config)).rejects.toThrow('Invalid config');
    });
  });

  describe('getTrainingJobStatus', () => {
    it('should get job status successfully', async () => {
      const mockJob = {
        job_id: 'job_123',
        status: 'running',
        config: { model_name: 'test-model' },
        progress: { epoch: 1, step: 50 }
      };

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockJob)
      });

      const result = await getTrainingJobStatus('job_123');

      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/training/jobs/job_123',
        expect.objectContaining({
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        })
      );

      expect(result).toEqual(mockJob);
    });
  });

  describe('listTrainingJobs', () => {
    it('should list training jobs with parameters', async () => {
      const mockResponse = {
        jobs: [{ job_id: 'job_1' }, { job_id: 'job_2' }],
        total: 2,
        limit: 10,
        offset: 0
      };

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const result = await listTrainingJobs('running', 10, 0);

      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/training/jobs?status=running&limit=10&offset=0',
        expect.any(Object)
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('getAvailableModels', () => {
    it('should return available models from API', async () => {
      const mockModels = {
        models: [
          { id: 'model1', name: 'Model 1' },
          { id: 'model2', name: 'Model 2' }
        ]
      };

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockModels)
      });

      const result = await getAvailableModels();

      expect(result).toEqual(mockModels);
    });

    it('should return mock models when API fails', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false
      });

      const result = await getAvailableModels();

      expect(result.models).toHaveLength(2);
      expect(result.models[0].id).toBe('microsoft/DialoGPT-medium');
    });
  });

  describe('getTrainingPresets', () => {
    it('should return training presets', async () => {
      const result = await getTrainingPresets();

      expect(result.presets).toHaveLength(3);
      expect(result.presets[0]).toHaveProperty('id', 'legal-chat-finetune');
      expect(result.presets[1]).toHaveProperty('id', 'legal-classification');
      expect(result.presets[2]).toHaveProperty('id', 'legal-embedding-finetune');
    });
  });
});
