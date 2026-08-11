import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export const baseConfig = defineConfig({
  plugins: [react()],
  
  // Enhanced build configuration
  build: {
    // Code splitting for better performance
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor libraries
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          query: ['@tanstack/react-query'],
          store: ['zustand'],
          ui: ['@heroicons/react', 'framer-motion'],
          
          // Application chunks
          auth: ['./shared/components/auth/LoginPage.tsx', './shared/components/auth/ProtectedRoute.tsx'],
          api: ['./shared/api/client.ts'],
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
    
    // Performance optimizations
    chunkSizeWarningLimit: 1000,
  },
  
  // Path resolution
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@shared': resolve(__dirname, './shared'),
      '@user': resolve(__dirname, './src/user'),
      '@developer': resolve(__dirname, './src/developer'),
      '@components': resolve(__dirname, './shared/components'),
      '@store': resolve(__dirname, './shared/stores'),
      '@api': resolve(__dirname, './shared/api'),
    },
  },
  
  // Test configuration
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
  
  // Development server configuration
  server: {
    host: true, // Listen on all addresses
    proxy: {
      '/v1': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  
  // Environment variables
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  
  // Security headers for development
  preview: {
    host: true,
    headers: {
      'X-Frame-Options': 'DENY',
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
    },
  },
})
