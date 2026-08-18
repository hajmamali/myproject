import { defineConfig, mergeConfig } from 'vitest/config'
import { baseConfig } from './vite.base.config'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  return mergeConfig(baseConfig, {
    root: resolve(__dirname, 'user'),
    
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
        '@shared': resolve(__dirname, './shared'),
      }
    },
    
    // User application entry point
    build: {
      outDir: resolve(__dirname, 'dist/user'),
      emptyOutDir: true,
    },
    
    // User application development server
    server: {
      port: 3000,
    },
    
    // User application preview server
    preview: {
      port: 4173,
    },
  })
})