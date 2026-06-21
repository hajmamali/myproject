#!/bin/bash

# Dark Theme Color Replacements
# This script converts light theme to dark theme

for file in *.tsx; do
  echo "Processing $file..."
  
  # Background colors
  sed -i 's/bg-white\b/bg-slate-900/g' "$file"
  sed -i 's/bg-slate-50\b/bg-slate-800/g' "$file"
  sed -i 's/bg-slate-100\b/bg-slate-800\/80/g' "$file"
  sed -i 's/bg-gray-50\b/bg-slate-800/g' "$file"
  sed -i 's/bg-gray-100\b/bg-slate-800\/80/g' "$file"
  
  # Text colors
  sed -i 's/text-slate-900\b/text-slate-100/g' "$file"
  sed -i 's/text-slate-800\b/text-slate-200/g' "$file"
  sed -i 's/text-slate-700\b/text-slate-300/g' "$file"
  sed -i 's/text-slate-600\b/text-slate-400/g' "$file"
  sed -i 's/text-slate-500\b/text-slate-500/g' "$file"
  sed -i 's/text-gray-900\b/text-gray-100/g' "$file"
  sed -i 's/text-gray-800\b/text-gray-200/g' "$file"
  sed -i 's/text-gray-700\b/text-gray-300/g' "$file"
  sed -i 's/text-gray-600\b/text-gray-400/g' "$file"
  
  # Border colors
  sed -i 's/border-slate-200\b/border-slate-700/g' "$file"
  sed -i 's/border-slate-300\b/border-slate-600/g' "$file"
  sed -i 's/border-gray-200\b/border-slate-700/g' "$file"
  sed -i 's/border-gray-300\b/border-slate-600/g' "$file"
  
  # Hover states
  sed -i 's/hover:bg-slate-50\b/hover:bg-slate-800/g' "$file"
  sed -i 's/hover:bg-slate-100\b/hover:bg-slate-700/g' "$file"
  sed -i 's/hover:bg-gray-50\b/hover:bg-slate-800/g' "$file"
  
  # Ring colors (focus states)
  sed -i 's/ring-slate-200\b/ring-slate-700/g' "$file"
  sed -i 's/ring-slate-300\b/ring-slate-600/g' "$file"
done

echo "✅ Dark theme applied to all components!"
