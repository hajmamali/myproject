/**
 * Training API Client — canonical implementation lives in shared/.
 */

export {
  startTrainingJob,
  getTrainingJobStatus,
  listTrainingJobs,
  stopTrainingJob,
  deleteTrainingJob,
  getAvailableModels,
  getTrainingPresets,
  type TrainingConfig,
  type TrainingJob,
  type TrainingJobResponse,
} from '@shared/api/trainingClient';

/** @deprecated Use getAvailableModels — kept for existing component imports */
export { getAvailableModels as listAvailableModels } from '@shared/api/trainingClient';
