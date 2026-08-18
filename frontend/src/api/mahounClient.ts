/**
 * MahouN API Client — canonical implementation lives in shared/.
 */

export * from '@shared/api/mahounClient';

/** Legacy alias used by a few components/tests */
export { retryDLQJob as retryJob } from '@shared/api/mahounClient';
