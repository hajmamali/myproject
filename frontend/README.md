# MAHOUN Legal Search UI

رابط کاربری وب جستجوی آراء حقوقی ماحون

A React + TypeScript web interface for searching legal verdicts in the MAHOUN system.

## Features

- 🔍 **Semantic Search**: Natural language search in Persian
- 🔧 **Advanced Filters**: Filter by court level, case type, finality, articles, and tags
- 📊 **Rich Results**: Display verdict chunks with relevance scores and metadata
- 🎨 **RTL Support**: Full right-to-left layout for Persian text
- ⚡ **Fast**: Built with Vite for instant HMR and optimized builds

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first styling
- **Vazirmatn** - Persian-optimized font

## Prerequisites

- Node.js 18+ and npm
- MAHOUN backend running at `http://localhost:8000`

## Run Backend

From the repository root:

```bash
# Start the FastAPI backend
python run.py api --reload
```

Backend will be available at: http://localhost:8000

**Important**: Make sure CORS is enabled on the backend. The backend already has CORS middleware configured.

## Run Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:5173

## Build for Production

```bash
cd frontend
npm run build
```

Built files will be in `frontend/dist/`.

## Project Structure

```
frontend/
├── public/
│   └── vite.svg              # Favicon
├── src/
│   ├── api/
│   │   ├── client.ts         # API client for backend calls
│   │   └── types.ts          # TypeScript interfaces
│   ├── components/
│   │   ├── LegalSearchPage.tsx   # Main page component
│   │   ├── SearchFilters.tsx     # Filters panel
│   │   ├── ResultsList.tsx       # Results container
│   │   ├── ResultCard.tsx        # Single result card
│   │   ├── ExportButton.tsx      # Export functionality
│   │   ├── UploadModal.tsx       # Document upload
│   │   └── StatsPanel.tsx        # System statistics
│   ├── App.tsx               # Root component
│   ├── main.tsx              # Entry point
│   └── index.css             # Global styles + Tailwind
├── index.html                # HTML template
├── package.json              # Dependencies
├── tailwind.config.js        # Tailwind configuration
├── vite.config.ts            # Vite configuration
└── tsconfig.json             # TypeScript configuration
```

## API Integration

The frontend calls the backend endpoint:

```
POST /v1/search/verdicts
```

Request body:
```json
{
  "query": "اعتراض ثالث اجرایی",
  "filters": {
    "court_level": "دادگاه تجدیدنظر استان",
    "is_final": true
  },
  "limit": 10
}
```

Response:
```json
{
  "results": [
    {
      "verdict_id": "verdict_001",
      "score": 0.85,
      "section": "appeal_reasoning",
      "chunk_text": "...",
      "case_type": "اعتراض ثالث اجرایی / رفع توقیف",
      "court_level": "دادگاه تجدیدنظر استان",
      "is_final": true,
      "tags": ["اعتراض ثالث اجرایی"],
      "law_articles": ["ماده 348 قانون آیین دادرسی مدنی"]
    }
  ],
  "total": 1,
  "query": "اعتراض ثالث اجرایی"
}
```

## Environment Variables

Create a `.env` file to customize settings:

```env
# Backend API URL (defaults to http://localhost:8000)
VITE_API_URL=http://localhost:8000
```

## Development

```bash
# Run linting
npm run lint

# Preview production build
npm run preview
```

## License

Part of the MAHOUN Legal AI System.

