# MEGAPROMPT Web Application

A modern web interface for MEGAPROMPT, built with Django REST Framework (backend) and Next.js with shadcn/ui (frontend).

## Quick Start

The easiest way to launch the web app is using the CLI command:

```bash
megaprompt web
```

This command will:
- Check for required dependencies (Python 3.10+, Node.js 18+, npm)
- Set up the Django backend project
- Set up the Next.js frontend project
- Install all dependencies
- Start both servers
- Open the app in your browser

## Manual Setup

If you prefer to set up manually:

### Backend Setup

1. Navigate to the backend directory:
```bash
cd webapp/backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations (if needed):
```bash
python manage.py migrate
```

4. Start the server:
```bash
python manage.py runserver
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd webapp/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Features

### Generate Mega-Prompt
- Transform user prompts into structured mega-prompts
- Configure LLM provider and settings
- Real-time progress tracking
- Download results in multiple formats

### Analyze Codebase
- Analyze codebases for system holes and architectural risks
- Multiple analysis modes
- Export analysis results

### Configuration Management
- Manage LLM provider settings
- Configure API keys
- Set preferences

### Cache & Checkpoints
- View cache statistics
- Manage checkpoints from previous runs
- Clear cache when needed

## Architecture

### Backend (Django REST Framework)
- RESTful API endpoints
- Background job processing
- Integration with MEGAPROMPT core functionality
- CORS enabled for local development

### Frontend (Next.js + shadcn/ui)
- Modern React-based UI
- Dark theme
- Responsive design
- Real-time updates via polling

## API Endpoints

- `POST /api/generate/` - Start prompt generation
- `GET /api/generate/{job_id}/` - Get generation result
- `POST /api/analyze/` - Start codebase analysis
- `GET /api/analyze/{job_id}/` - Get analysis result
- `GET /api/config/` - Get configuration
- `POST /api/config/` - Update configuration
- `GET /api/cache/` - Get cache statistics
- `DELETE /api/cache/` - Clear cache
- `GET /api/checkpoints/` - List checkpoints
- `GET /api/checkpoints/{id}/` - Get checkpoint details
- `DELETE /api/checkpoints/{id}/` - Delete checkpoint

## Development

The web app is designed for local development only. Both servers should be running simultaneously:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

The frontend proxies API requests to the backend automatically.

## Troubleshooting

### Port Already in Use
If ports 8000 or 3000 are already in use, you can specify custom ports:
```bash
megaprompt web --port-backend 8001 --port-frontend 3001
```

### Missing Dependencies
If you encounter missing dependencies, try:
```bash
megaprompt web --reinstall
```

### Skip Setup
If the project is already set up:
```bash
megaprompt web --skip-setup
```

