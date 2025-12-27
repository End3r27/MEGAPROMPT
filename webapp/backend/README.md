# MEGAPROMPT Web Backend

Django REST Framework backend for MEGAPROMPT web application.

## Setup

The backend is automatically set up when you run `megaprompt web`. However, if you need to set it up manually:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Start server:
```bash
python manage.py runserver
```

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

## Integration

The backend integrates with MEGAPROMPT core functionality through the `core/services.py` module, which wraps:
- `MegaPromptPipeline` for prompt generation
- `AnalysisPipeline` for codebase analysis
- `Config` for configuration management
- Cache and checkpoint management

