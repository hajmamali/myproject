#!/usr/bin/env node
/**
 * Frontend Architecture Dependency Check
 * Ensures user application doesn't import developer-only modules
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REPO_ROOT = path.resolve(__dirname, '..');
const FRONTEND_USER_DIR = path.join(REPO_ROOT, 'user');

// Patterns that indicate developer-only imports
const DEVELOPER_IMPORT_PATTERNS = [
  'from.*developer',
  'from.*GovernanceCenter',
  'from.*DatasetEngineering', 
  'from.*StudioLayout',
  'from.*pages/GovernanceCenter',
  'from.*pages/DatasetEngineering',
  'from.*pages/FineTuningDashboard',
];

async function checkUserImports() {
  console.log('���������������������������������������������������������������������������������������������🔍 Checking user application for forbidden developer imports...');
  
  // Get all user application files
  const userFiles = await getAllFiles(FRONTEND_USER_DIR, ['.ts', '.tsx']);
  
  let violations = [];
  
  for (const file of userFiles) {
    try {
      const content = await fs.promises.readFile(file, 'utf8');
      const relativePath = path.relative(REPO_ROOT, file);
      
      // Check for developer-only imports
      for (const pattern of DEVELOPER_IMPORT_PATTERNS) {
        const regex = new RegExp(pattern, 'i');
        if (regex.test(content)) {
          // Extract the import line for better reporting
          const lines = content.split('\n');
          for (let i = 0; i < lines.length; i++) {
            if (regex.test(lines[i])) {
              violations.push({
                file: relativePath,
                line: i + 1,
                content: lines[i].trim(),
                pattern: pattern
              });
              break;
            }
          }
        }
      }
    } catch (err) {
      console.error(`Error reading file ${file}:`, err);
    }
  }
  
  if (violations.length > 0) {
    console.log('��������������������������������������������������������������❌ FORBIDDEN IMPORTS DETECTED:');
    violations.forEach(v => {
      console.log(`  ${v.file}:${v.line}`);
      console.log(`    ${v.content}`);
      console.log();
    });
    process.exit(1);
  } else {
    console.log('��������������������������������������������������������������✅ No forbidden developer imports found in user application');
    process.exit(0);
  }
}

async function getAllFiles(dir, extensions) {
  let results = [];
  try {
    const files = await fs.promises.readdir(dir);
    
    for (const file of files) {
      const filePath = path.join(dir, file);
      try {
        const stat = await fs.promises.stat(filePath);
        
        if (stat.isDirectory()) {
          // Skip node_modules and dist directories
          if (!filePath.includes('node_modules') && !filePath.includes('dist')) {
            results = results.concat(await getAllFiles(filePath, extensions));
          }
        } else {
          const ext = path.extname(file);
          if (extensions.includes(ext)) {
            results.push(filePath);
          }
        }
      } catch (statErr) {
        console.warn(`Could not stat file ${filePath}:`, statErr.message);
      }
    }
  } catch (readdirErr) {
    console.error(`Could not read directory ${dir}:`, readdirErr.message);
  }
  
  return results;
}

checkUserImports();