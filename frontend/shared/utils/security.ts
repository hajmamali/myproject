/**
 * MAHOUN Security Utilities
 * 
 * Security functions for:
 * - Input sanitization
 * - XSS protection
 * - Content validation
 */

import DOMPurify from 'dompurify';

/**
 * Sanitize HTML content to prevent XSS attacks
 */
export function sanitizeHTML(input: string): string {
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: [],
  });
}

/**
 * Sanitize text input for safe display
 */
export function sanitizeText(input: string): string {
  return input
    .replace(/[<>]/g, '') // Remove HTML brackets
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/on\w+=/gi, '') // Remove event handlers
    .trim();
}

/**
 * Validate and sanitize Persian text
 */
export function sanitizePersianText(input: string): string {
  // Remove potentially dangerous characters while preserving Persian
  const sanitized = input
    .replace(/[<>"']/g, '') // Remove HTML and quotes
    .replace(/javascript:/gi, '') // Remove javascript protocol
    .replace(/on\w+=/gi, '') // Remove event handlers
    .trim();
    
  return sanitized;
}

/**
 * Validate file name for security
 */
export function validateFileName(fileName: string): boolean {
  // Check for path traversal and dangerous characters
  const dangerousPatterns = [
    /\.\./,
    /\//,
    /\\/,
    /[<>:"|?*]/,
    /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i,
  ];
  
  return !dangerousPatterns.some(pattern => pattern.test(fileName));
}

/**
 * Generate secure request ID
 */
export function generateSecureId(prefix: string = 'id'): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substr(2, 9);
  return `${prefix}_${timestamp}_${random}`;
}

/**
 * Validate URL for safe redirection
 */
export function validateRedirectURL(url: string): boolean {
  try {
    const parsed = new URL(url, window.location.origin);
    
    // Only allow same-origin redirects
    return parsed.origin === window.location.origin;
  } catch {
    return false;
  }
}

/**
 * Content Security Policy violation reporter
 */
export function reportCSPViolation(violationEvent: SecurityPolicyViolationEvent): void {
  console.error('CSP Violation:', {
    blockedURI: violationEvent.blockedURI,
    documentURI: violationEvent.documentURI,
    effectiveDirective: violationEvent.effectiveDirective,
    originalPolicy: violationEvent.originalPolicy,
    referrer: violationEvent.referrer,
    violatedDirective: violationEvent.violatedDirective,
  });
  
  // In production, send to monitoring service
  if (process.env.NODE_ENV === 'production') {
    // Send to backend security monitoring
    fetch('/api/security/csp-violation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        blocked_uri: violationEvent.blockedURI,
        document_uri: violationEvent.documentURI,
        directive: violationEvent.effectiveDirective,
        timestamp: new Date().toISOString(),
      }),
    }).catch(console.error);
  }
}

/**
 * Initialize security event listeners
 */
export function initializeSecurity(): void {
  // Listen for CSP violations
  document.addEventListener('securitypolicyviolation', reportCSPViolation);
  
  // Prevent drag and drop of external content
  document.addEventListener('dragover', (e) => e.preventDefault());
  document.addEventListener('drop', (e) => e.preventDefault());
  
  // Log potential security issues
  window.addEventListener('error', (e) => {
    if (e.message.includes('Script error')) {
      console.warn('Potential cross-origin script error detected');
    }
  });
}

/**
 * Cleanup security event listeners
 */
export function cleanupSecurity(): void {
  document.removeEventListener('securitypolicyviolation', reportCSPViolation);
}