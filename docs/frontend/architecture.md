# MAHOUN Frontend Architecture

**Classification:** MANDATORY FRONTEND DOCUMENTATION  
**Version:** 2.0.0  
**Status:** Normative  
**Last Updated:** 2026-08-06  

---

## Overview

MAHOUN Frontend is a **modern React 18 application** built with TypeScript, providing a sophisticated interface for legal AI reasoning with zero-hallucination guarantees. The architecture emphasizes **governance-first design**, **audit-grade compliance**, and **enterprise security**.

### Core Technologies

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| **React** | 18.2+ | UI Framework | ✅ Production |
| **TypeScript** | 5.0+ | Type Safety | ✅ Production |
| **Vite** | 4.0+ | Build Tool | ✅ Production |
| **TailwindCSS** | 3.3+ | Styling | ✅ Production |
| **Zustand** | 4.4+ | State Management | ✅ Production |
| **React Query** | 4.0+ | Server State | ✅ Production |

---

## Frontend Framework

### React 18 Architecture

```typescript
// Core Application Structure
src/
├── components/           # Reusable UI components
│   ├── common/          # Generic components (Button, Input, Modal)
│   ├── legal/           # Legal-specific components
│   └── governance/      # Governance and audit components
├── pages/               # Route-level page components
├── hooks/               # Custom React hooks
├── services/            # API client services
├── store/               # Zustand state stores
├── types/               # TypeScript type definitions
├── utils/               # Utility functions
└── api/                 # API client configuration
```

### Component Architecture

```typescript
// Component Hierarchy Pattern
interface ComponentProps {
  // Props with governance context
  governanceContext?: GovernanceContext;
  auditTrail?: AuditTrail;
  
  // Standard props
  children?: React.ReactNode;
  className?: string;
}

// Base component with governance integration
export const BaseComponent: React.FC<ComponentProps> = ({
  governanceContext,
  auditTrail,
  children,
  ...props
}) => {
  // Governance hooks
  const { validateAccess } = useGovernance(governanceContext);
  const { logInteraction } = useAuditTrail(auditTrail);
  
  return (
    <div {...props}>
      {children}
    </div>
  );
};
```

### React 18 Features Integration

1. **Concurrent Features:** Automatic batching and Suspense for better UX
2. **Server Components:** Future-ready architecture for SSR integration
3. **Error Boundaries:** Comprehensive error handling and recovery
4. **Strict Mode:** Development-time safety and future-proofing

---

## State Management

### Zustand Store Architecture

```typescript
// Authentication Store
interface AuthState {
  isAuthenticated: boolean;
  user: UserIdentity | null;
  token: string | null;
  permissions: Permission[];
  governanceContext: GovernanceContext;
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateGovernanceContext: (context: GovernanceContext) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: false,
  user: null,
  token: null,
  permissions: [],
  governanceContext: {},
  
  login: async (credentials) => {
    const response = await authAPI.login(credentials);
    set({
      isAuthenticated: true,
      user: response.user,
      token: response.token,
      permissions: response.permissions,
      governanceContext: response.governanceContext,
    });
  },
  
  logout: () => {
    set({
      isAuthenticated: false,
      user: null,
      token: null,
      permissions: [],
      governanceContext: {},
    });
  },
}));
```

### Legal Reasoning Store

```typescript
interface LegalReasoningState {
  // Case Management
  currentCase: LegalCase | null;
  cases: LegalCase[];
  
  // Reasoning State
  reasoningSession: ReasoningSession | null;
  evidenceGraph: EvidenceNode[];
  contradictions: Contradiction[];
  
  // Actions
  createCase: (caseData: CreateCaseRequest) => Promise<LegalCase>;
  executeReasoning: (query: ReasoningQuery) => Promise<ReasoningResult>;
  validateEvidence: (evidence: Evidence) => Promise<ValidationResult>;
}
```
### Store Composition Pattern

```typescript
// Combined store with governance
interface AppState extends AuthState, LegalReasoningState {
  governance: GovernanceState;
  audit: AuditState;
  ui: UIState;
}

// Store composition with middleware
export const useAppStore = create<AppState>()(
  devtools(
    persist(
      governanceMiddleware(
        auditMiddleware(
          (set, get) => ({
            ...createAuthSlice(set, get),
            ...createLegalReasoningSlice(set, get),
            ...createGovernanceSlice(set, get),
            ...createAuditSlice(set, get),
            ...createUISlice(set, get),
          })
        )
      ),
      { name: 'mahoun-store' }
    )
  )
);
```

---

## Authentication Integration

### Authentication Flow

```typescript
// Authentication hook with governance
export const useAuthentication = () => {
  const auth = useAuthStore();
  const { validateSession } = useGovernanceValidation();
  
  const authenticatedFetch = useCallback(async (url: string, options: RequestInit = {}) => {
    // Validate session with governance
    await validateSession(auth.governanceContext);
    
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${auth.token}`,
      'X-Request-ID': generateRequestId(),
      'X-Governance-Context': JSON.stringify(auth.governanceContext),
    };
    
    return fetch(url, { ...options, headers });
  }, [auth.token, auth.governanceContext]);
  
  return {
    ...auth,
    authenticatedFetch,
    isAuthorized: (permission: Permission) => auth.permissions.includes(permission),
  };
};
```

### Protected Route System

```typescript
// Route protection with granular permissions
export const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  requiredPermissions: Permission[];
  fallback?: React.ReactNode;
}> = ({ children, requiredPermissions, fallback }) => {
  const { isAuthenticated, permissions } = useAuthentication();
  const hasPermissions = requiredPermissions.every(p => permissions.includes(p));
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  if (!hasPermissions) {
    return fallback || <UnauthorizedPage />;
  }
  
  return <>{children}</>;
};
```
### Authentication Context Integration

```typescript
// Governance-aware authentication provider
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const auth = useAuthStore();
  
  // Governance context initialization
  useEffect(() => {
    if (auth.isAuthenticated) {
      initializeGovernanceContext(auth.user, auth.token);
    }
  }, [auth.isAuthenticated]);
  
  // Session validation with governance
  useEffect(() => {
    const interval = setInterval(async () => {
      if (auth.isAuthenticated) {
        await validateSessionGovernance(auth.governanceContext);
      }
    }, 60000); // Validate every minute
    
    return () => clearInterval(interval);
  }, [auth.isAuthenticated]);
  
  return (
    <GovernanceProvider context={auth.governanceContext}>
      <AuditProvider>
        {children}
      </AuditProvider>
    </GovernanceProvider>
  );
};
```

---

## API Client Architecture

### Governance-First API Client

```typescript
// API client with built-in governance
class MahounAPIClient {
  private baseURL: string;
  private governanceContext: GovernanceContext;
  
  constructor(baseURL: string) {
    this.baseURL = baseURL;
    this.governanceContext = {};
  }
  
  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<APIResponse<T>> {
    // Pre-request governance validation
    await this.validateGovernanceCompliance(endpoint, options);
    
    const headers = {
      'Content-Type': 'application/json',
      'X-Request-ID': generateRequestId(),
      'X-Trace-ID': generateTraceId(),
      'X-Governance-Context': JSON.stringify(this.governanceContext),
      ...options.headers,
    };
    
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
    });
    
    // Post-response governance validation
    await this.validateResponseGovernance(response);
    
    return this.parseResponse<T>(response);
  }
  
  // Specialized methods for legal operations
  async executeReasoning(query: ReasoningQuery): Promise<ReasoningResult> {
    return this.request<ReasoningResult>('/api/v1/reasoning/execute', {
      method: 'POST',
      body: JSON.stringify(query),
    });
  }
  
  async validateEvidence(evidence: Evidence): Promise<ValidationResult> {
    return this.request<ValidationResult>('/api/v1/evidence/validate', {
      method: 'POST',
      body: JSON.stringify(evidence),
    });
  }
}
```
### React Query Integration

```typescript
// Custom hooks with governance integration
export const useReasoningQuery = (query: ReasoningQuery) => {
  const { authenticatedFetch } = useAuthentication();
  const { validateQuery } = useGovernanceValidation();
  
  return useQuery({
    queryKey: ['reasoning', query],
    queryFn: async () => {
      // Pre-query governance validation
      await validateQuery(query);
      
      const response = await authenticatedFetch('/api/v1/reasoning/execute', {
        method: 'POST',
        body: JSON.stringify(query),
      });
      
      return response.json();
    },
    staleTime: 0, // Always fresh for legal reasoning
    cacheTime: 300000, // Cache for 5 minutes
    retry: false, // No retries for legal operations
  });
};

export const useEvidenceValidation = () => {
  const { authenticatedFetch } = useAuthentication();
  
  return useMutation({
    mutationFn: async (evidence: Evidence) => {
      const response = await authenticatedFetch('/api/v1/evidence/validate', {
        method: 'POST',
        body: JSON.stringify(evidence),
      });
      return response.json();
    },
    onSuccess: (result) => {
      // Update evidence cache
      queryClient.setQueryData(['evidence', evidence.id], result);
    },
  });
};
```

---

## Component System

### Design System Components

```typescript
// Base UI components with governance integration
export const Button: React.FC<ButtonProps & GovernanceProps> = ({
  children,
  onClick,
  governanceContext,
  auditAction,
  ...props
}) => {
  const { logInteraction } = useAuditTrail();
  
  const handleClick = useCallback(async (event: React.MouseEvent) => {
    // Log interaction for audit
    await logInteraction({
      action: auditAction || 'button_click',
      context: governanceContext,
      timestamp: new Date().toISOString(),
    });
    
    onClick?.(event);
  }, [onClick, auditAction, governanceContext]);
  
  return (
    <button
      {...props}
      onClick={handleClick}
      className={cn(buttonVariants({ variant: props.variant }), props.className)}
    >
      {children}
    </button>
  );
};
```

### Legal-Specific Components

```typescript
// Evidence viewer with validation
export const EvidenceViewer: React.FC<{
  evidence: Evidence;
  showValidation?: boolean;
}> = ({ evidence, showValidation = true }) => {
  const { data: validation, isLoading } = useQuery({
    queryKey: ['evidence-validation', evidence.id],
    queryFn: () => validateEvidence(evidence),
    enabled: showValidation,
  });
  
  return (
    <Card className="evidence-viewer">
      <CardHeader>
        <CardTitle>Evidence: {evidence.title}</CardTitle>
        {showValidation && (
          <ValidationBadge 
            status={validation?.status} 
            isLoading={isLoading} 
          />
        )}
      </CardHeader>
      <CardContent>
        <EvidenceContent content={evidence.content} />
        {validation && (
          <ValidationDetails validation={validation} />
        )}
      </CardContent>
    </Card>
  );
};
```
---

## Routing Architecture

### React Router with Governance

```typescript
// Route configuration with permissions
interface RouteConfig {
  path: string;
  component: React.ComponentType;
  requiredPermissions: Permission[];
  governanceLevel: 'public' | 'authenticated' | 'restricted';
}

const routes: RouteConfig[] = [
  {
    path: '/',
    component: Dashboard,
    requiredPermissions: [Permission.READ],
    governanceLevel: 'authenticated',
  },
  {
    path: '/legal/reasoning',
    component: LegalReasoningPage,
    requiredPermissions: [Permission.READ, Permission.WRITE],
    governanceLevel: 'restricted',
  },
  {
    path: '/admin',
    component: AdminPanel,
    requiredPermissions: [Permission.ADMIN],
    governanceLevel: 'restricted',
  },
];

// Router with governance enforcement
export const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {routes.map((route) => (
          <Route
            key={route.path}
            path={route.path}
            element={
              <ProtectedRoute requiredPermissions={route.requiredPermissions}>
                <GovernanceWrapper level={route.governanceLevel}>
                  <route.component />
                </GovernanceWrapper>
              </ProtectedRoute>
            }
          />
        ))}
      </Routes>
    </BrowserRouter>
  );
};
```

---

## Error Handling & Recovery

### Error Boundary System

```typescript
// Governance-aware error boundary
export class GovernanceErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; errorInfo: any }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, errorInfo: null };
  }
  
  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }
  
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to governance system
    logGovernanceError({
      error: error.message,
      stack: error.stack,
      errorInfo,
      timestamp: new Date().toISOString(),
    });
    
    this.setState({ errorInfo });
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <ErrorFallback 
          error={this.state.errorInfo} 
          onRetry={() => this.setState({ hasError: false })}
        />
      );
    }
    
    return this.props.children;
  }
}
```

### Recovery Mechanisms

```typescript
// Error recovery with audit trails
export const useErrorRecovery = () => {
  const { logAuditEvent } = useAuditTrail();
  
  const recoverFromError = useCallback(async (error: Error, context: any) => {
    // Log recovery attempt
    await logAuditEvent({
      type: 'error_recovery_attempt',
      error: error.message,
      context,
      timestamp: new Date().toISOString(),
    });
    
    // Attempt recovery strategies
    try {
      // Clear corrupted state
      clearCorruptedState(context);
      
      // Reload essential data
      await reloadEssentialData();
      
      // Notify user
      showRecoveryNotification('System recovered successfully');
      
    } catch (recoveryError) {
      // Log failed recovery
      await logAuditEvent({
        type: 'error_recovery_failed',
        originalError: error.message,
        recoveryError: recoveryError.message,
        timestamp: new Date().toISOString(),
      });
      
      throw recoveryError;
    }
  }, [logAuditEvent]);
  
  return { recoverFromError };
};
```
---

## Performance & Security

### Code Splitting & Lazy Loading

```typescript
// Route-based code splitting with governance
const LazyLegalReasoningPage = React.lazy(() =>
  import('./pages/LegalReasoningPage').then(module => ({
    default: withGovernance(module.default)
  }))
);

const LazyAdminPanel = React.lazy(() =>
  import('./pages/AdminPanel').then(module => ({
    default: withGovernance(module.default)
  }))
);

// Suspense with governance loading
export const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Suspense fallback={<GovernanceLoadingSpinner />}>
        <Routes>
          <Route 
            path="/legal/reasoning" 
            element={<LazyLegalReasoningPage />} 
          />
          <Route 
            path="/admin" 
            element={<LazyAdminPanel />} 
          />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
};
```

### Security Measures

```typescript
// Content Security Policy configuration
export const securityConfig = {
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", process.env.VITE_API_BASE_URL],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"],
    },
  },
  
  // Additional security headers
  headers: {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
  },
};

// Input sanitization
export const sanitizeInput = (input: string): string => {
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p', 'br'],
    ALLOWED_ATTR: [],
  });
};
```

---

## Development & Build

### Vite Configuration

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [
    react(),
    // Governance plugin for build-time validation
    governanceValidationPlugin(),
  ],
  
  build: {
    // Code splitting configuration
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@headlessui/react', '@heroicons/react'],
          legal: ['./src/components/legal'],
          governance: ['./src/components/governance'],
        },
      },
    },
    
    // Security optimizations
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
  },
  
  // Development server configuration
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL,
        changeOrigin: true,
        secure: true,
      },
    },
  },
});
```

### TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/components/*": ["./src/components/*"],
      "@/hooks/*": ["./src/hooks/*"],
      "@/services/*": ["./src/services/*"]
    }
  }
}
```
---

## Deployment & Configuration

### Environment Configuration

```typescript
// Environment variables with validation
interface EnvironmentConfig {
  // API Configuration
  VITE_API_BASE_URL: string;
  VITE_API_TIMEOUT: number;
  
  // Authentication
  VITE_AUTH_PROVIDER: 'api_key' | 'session' | 'both';
  VITE_SESSION_TIMEOUT: number;
  
  // Governance
  VITE_GOVERNANCE_MODE: 'strict' | 'permissive';
  VITE_AUDIT_LEVEL: 'minimal' | 'standard' | 'comprehensive';
  
  // Features
  VITE_ENABLE_DEVELOPMENT_TOOLS: boolean;
  VITE_ENABLE_ANALYTICS: boolean;
}

// Environment validation
export const validateEnvironment = (): EnvironmentConfig => {
  const config = {
    VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
    VITE_API_TIMEOUT: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
    VITE_AUTH_PROVIDER: import.meta.env.VITE_AUTH_PROVIDER || 'session',
    VITE_SESSION_TIMEOUT: Number(import.meta.env.VITE_SESSION_TIMEOUT) || 3600,
    VITE_GOVERNANCE_MODE: import.meta.env.VITE_GOVERNANCE_MODE || 'strict',
    VITE_AUDIT_LEVEL: import.meta.env.VITE_AUDIT_LEVEL || 'standard',
    VITE_ENABLE_DEVELOPMENT_TOOLS: import.meta.env.DEV || false,
    VITE_ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  };
  
  // Validate required variables
  if (!config.VITE_API_BASE_URL) {
    throw new Error('VITE_API_BASE_URL is required');
  }
  
  return config as EnvironmentConfig;
};
```

### Production Optimization

```typescript
// Production build optimizations
export const productionConfig = {
  // Bundle analysis
  analyze: process.env.ANALYZE === 'true',
  
  // Performance budgets
  performanceBudgets: {
    maxAssetSize: 500000, // 500KB
    maxEntrypointSize: 1000000, // 1MB
  },
  
  // Caching strategy
  cacheStrategy: {
    staticAssets: '1y', // Cache static assets for 1 year
    apiResponses: '5m', // Cache API responses for 5 minutes
    userSessions: '1h', // Cache user sessions for 1 hour
  },
  
  // Progressive Web App configuration
  pwa: {
    registerType: 'autoUpdate',
    workbox: {
      globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
      runtimeCaching: [
        {
          urlPattern: /^https:\/\/api\./,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'api-cache',
            expiration: {
              maxEntries: 100,
              maxAgeSeconds: 300, // 5 minutes
            },
          },
        },
      ],
    },
  },
};
```

---

## Governance Integration

### Constitutional Compliance

All frontend components must comply with constitutional requirements:

1. **Fail-Closed Architecture:** Frontend fails securely when backend is unavailable
2. **Audit Trails:** Every user interaction generates audit events
3. **Permission Validation:** All UI actions validate permissions before execution
4. **Data Integrity:** All data displays include integrity validation
5. **Zero-Hallucination:** No speculative UI states without backend confirmation

### Governance Middleware

```typescript
// Frontend governance middleware
export const governanceMiddleware = (store: any) => (next: any) => (action: any) => {
  // Pre-action governance validation
  if (requiresGovernanceValidation(action)) {
    validateActionGovernance(action);
  }
  
  // Execute action
  const result = next(action);
  
  // Post-action audit logging
  if (requiresAuditLogging(action)) {
    logActionAudit(action, result);
  }
  
  return result;
};
```

---

## Future Enhancements

### Planned Features

1. **Real-time Updates:** WebSocket integration for live legal reasoning
2. **Offline Capability:** Service worker for offline legal document access
3. **Advanced Analytics:** Legal reasoning performance metrics
4. **Mobile Optimization:** Responsive design for tablet and mobile devices
5. **Accessibility:** WCAG 2.1 AA compliance for legal professionals with disabilities

### Technical Roadmap

| Phase | Timeline | Features |
|-------|----------|----------|
| **Phase 1** | Q3 2026 | Enhanced mobile experience, offline capabilities |
| **Phase 2** | Q4 2026 | Real-time collaboration, advanced analytics |
| **Phase 3** | Q1 2027 | AI-powered UI recommendations, voice interface |

---

## References

### Core Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0",
    "vite": "^4.0.0",
    "tailwindcss": "^3.3.0",
    "zustand": "^4.4.0",
    "@tanstack/react-query": "^4.0.0",
    "react-router-dom": "^6.0.0",
    "@headlessui/react": "^1.7.0",
    "@heroicons/react": "^2.0.0"
  }
}
```

### Integration Points

- **Backend API:** `/api/v1/` REST endpoints with governance headers
- **Authentication:** Integration with `mahoun.security.rbac` system  
- **Governance:** Direct integration with constitutional framework
- **Audit System:** Integration with `mahoun.audit` package

---

*This document is part of the MAHOUN Constitutional Framework and is subordinate to `mahoun/constitutional/constitution/CONSTITUTION.md` for all governance matters.*