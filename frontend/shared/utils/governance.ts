/**
 * Governance ID Generator Utility
 * 
 * Generates unique identifiers for governance and audit purposes
 */

export function generateRequestId(): string {
  return 'req_' + Math.random().toString(36).substring(2, 18);
}

export function generateTraceId(): string {
  return 'trace_' + Math.random().toString(36).substring(2, 18);
}

export function generateAuditReference(): string {
  const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
  const time = Date.now().toString(36);
  return `audit_${date}_${time}`;
}