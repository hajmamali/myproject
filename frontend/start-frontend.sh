#!/bin/bash

# MAHOUN Frontend Startup Script

echo "🚀 Starting MAHOUN Frontend..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Start development server
echo "✨ Starting Vite dev server..."
echo "   Frontend will be available at: http://localhost:5173"
echo "   Make sure backend is running at: http://localhost:8000"
echo ""

npm run dev

