import { defineConfig, mergeConfig } from 'vitest/config'
import { baseConfig } from './vite.base.config'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  return mergeConfig(baseConfig, {
    root: resolve(__dirname, 'developer'),
    
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
        '@shared': resolve(__dirname, './shared'),
      }
    },
    
    // Developer application entry point
    build: {
      outDir: resolve(__dirname, 'dist/developer'),
      emptyOutDir: true,
    },
    
    // Developer application development server
    server: {
      port: 3001,
    },
    
    // Developer application preview server
    preview: {
      port: 4174,
    },
  })
})