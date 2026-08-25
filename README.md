# AI CMS - Production-Ready Modular AI Content Management System

A WordPress-like, production-oriented CMS platform built with Python, Django, Wagtail, LangChain, LangGraph, and Qdrant. Designed for zero-touch configuration after initial deployment.

## Features

### 🎯 Core CMS
- **Page Management**: Drag-and-drop page builder with StreamField blocks
- **Dynamic Content**: Configurable page types (Home, Standard, Landing, Chat, Knowledge Base)
- **Branding**: Theme colors, typography, logos—all editable through admin
- **Navigation**: Admin-managed menus with unlimited nesting
- **Multi-tenancy**: Support for multiple sites/organizations
- **Publishing Workflow**: Draft, review, publish, schedule, revision history

### 🤖 AI Integration
- **LLM Provider Abstraction**: Support for OpenAI, Google Gemini, Groq, Ollama, local OpenAI-compatible APIs
- **Multi-Provider**: Run different models for different use cases simultaneously
- **Configurable Prompts**: Template-based, versioned, approved prompts
- **RAG (Retrieval Augmented Generation)**: LangGraph-powered workflow with configurable nodes
- **Knowledge Bases**: Multiple Qdrant collections with configurable retrieval

### 📚 Document Ingestion
- **Excel/CSV Mapping**: Column configuration and preview before ingestion
- **Multi-Format Support**: PDF, DOCX, TXT, MD, HTML, JSON
- **Chunking**: Configurable chunk size and overlap
- **Batch Processing**: Celery-powered background jobs with progress tracking
- **Duplicate Detection**: Checksum-based deduplication
- **Error Handling**: Comprehensive retry and error logging

### 🔗 Connector Framework
- **Jira Integration**: REST API connector with incremental sync
- **Confluence Integration**: Page hierarchy and attachment handling
- **Extensible Design**: Abstract connector interface for future data sources
- **Scheduled Sync**: Celery Beat for automatic synchronization
- **Rate Limiting**: Built-in backoff and retry strategies

### 💬 Public Chat Experience
- **Streaming Responses**: Real-time response generation
- **Citation Display**: Source cards with evidence
- **Conversation History**: Persistent chat sessions
- **Mobile Responsive**: Accessible on all devices
- **Throttling & Security**: Rate limiting and CSRF protection

### 🛡️ Security & Governance
- **Permission System**: Django groups with granular permissions
- **Tenant Isolation**: Complete data separation
- **Secret Management**: Environment variables + encrypted storage
- **Audit Logging**: Complete action history
- **No Arbitrary Code Execution**: All configuration through UI

## Quick Start (Linux/macOS)

### Prerequisites
- Python 3.12+
- PostgreSQL (or SQLite for development)
- Redis (optional, for background jobs)
- Qdrant (for vector search)

### Installation

```bash
# Clone or navigate to project
cd ai-cms

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements/development.txt

# Create environment file
cp .env.example .env

# Run migrations
python manage.py migrate

# Setup AI CMS (creates groups, site config, etc.)
python manage.py setup_ai_cms

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

Visit `http://localhost:8000/admin` to access Wagtail admin interface.

### Running Optional Services

```bash
# Terminal 1: Development server
python manage.py runserver

# Terminal 2: Celery worker (if using background jobs)
celery -A config worker --loglevel=info

# Terminal 3: Celery beat (if using scheduled jobs)
celery -A config beat --loglevel=info

# Redis (via Docker)
docker run -d -p 6379:6379 redis:latest

# Qdrant (via Docker)
docker run -d -p 6333:6333 qdrant/qdrant
```

## Project Structure

```
ai_cms/
├── config/                 # Django settings and configuration
│   ├── settings/
│   │   ├── base.py        # Shared configuration
│   │   ├── development.py # Dev-specific settings
│   │   └── production.py  # Production settings
│   ├── urls.py            # URL routing
│   ├── celery.py          # Celery configuration
│   └── wsgi.py
├── apps/
│   ├── core/              # Core utilities and base models
│   ├── tenants/           # Multi-tenancy support
│   ├── accounts/          # User management
│   ├── branding/          # Site branding configuration
│   ├── navigation/        # Menu system
│   ├── ai_providers/      # LLM provider registry
│   ├── prompts/           # Prompt template management
│   ├── knowledge/         # Knowledge base models
│   ├── ingestion/         # Document ingestion pipeline
│   ├── connectors/        # Data connectors (Jira, Confluence)
│   ├── retrieval/         # RAG retrieval service
│   ├── workflows/         # LangGraph workflow orchestration
│   ├── conversations/     # Chat and conversation models
│   ├── audit/             # Audit logging
│   ├── observability/     # Health checks and metrics
│   └── api/               # REST API endpoints
├── home/                  # Wagtail home page app
├── search/                # Wagtail search app
├── templates/             # Global templates
├── static/                # Static files (CSS, JS)
├── media/                 # User uploads
├── requirements/
│   ├── base.txt          # Core dependencies
│   ├── development.txt   # Dev dependencies
│   └── production.txt    # Production dependencies
└── docs/                  # Documentation
```

## Configuration

### Environment Variables (.env)

```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3
# For PostgreSQL: postgres://user:password@localhost:5432/ai_cms

# Cache & Background Jobs
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# AI Providers
OPENAI_API_KEY=
GOOGLE_GENAI_API_KEY=
GROQ_API_KEY=

# Local LLMs
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_OPENAI_BASE_URL=http://localhost:8000

# Other
DEFAULT_TENANT_SLUG=default
LOG_LEVEL=INFO
```

### Django Admin Configuration

After creating a superuser, access the admin at `/admin/` and:

1. **Configure AI Providers** (`AI Providers` section)
   - Add OpenAI, Gemini, or other providers
   - Test connections

2. **Create Knowledge Base**
   - Connect to Qdrant
   - Configure embedding model
   - Set retrieval parameters

3. **Upload Documents**
   - Use "Add Document" to upload Excel, PDF, etc.
   - Map columns (for spreadsheets)
   - Start ingestion job

4. **Create AI Assistant**
   - Configure prompt template
   - Select knowledge bases
   - Configure LLM model
   - Publish to site

5. **Manage Navigation**
   - Create menus
   - Configure header/footer
   - Add internal/external links

## API Endpoints

Versioned REST API at `/api/v1/`:

```
POST   /api/v1/chat/              # Submit prompt
GET    /api/v1/chat/stream/       # Stream response
GET    /api/v1/conversations/     # List conversations
GET    /api/v1/assistants/        # List available assistants
GET    /api/v1/knowledge-bases/   # List knowledge bases
GET    /api/v1/health/            # Health check
GET    /api/v1/ready/             # Readiness probe
```

## Development

### Running Tests

```bash
# All tests
pytest

# Specific app
pytest apps/ingestion/tests/

# With coverage
pytest --cov=apps --cov-report=html

# Watch mode
ptw
```

### Database Migrations

```bash
# Create migration
python manage.py makemigrations apps.ingestion

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

### Code Style

```bash
# Format code
black apps/

# Check linting
flake8 apps/

# Sort imports
isort apps/
```

## Production Deployment

### Prerequisites
- PostgreSQL database
- Redis instance
- Qdrant instance
- SSL certificate

### Setup

```bash
# Install production requirements
pip install -r requirements/production.txt

# Set production environment
export DJANGO_SETTINGS_MODULE=config.settings.production

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Run with gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Systemd Services

See `scripts/` directory for example systemd service files for:
- Django application
- Celery worker
- Celery beat

## Architecture Highlights

### Provider Abstraction
All LLM and embedding providers are accessed through abstract interfaces, allowing:
- Easy addition of new providers
- Provider switching without code changes
- Fallback strategies
- Rate limiting per provider

### Connector Framework
Connectors implement a common interface:
- `validate_configuration()`
- `test_connection()`
- `preview()`
- `sync()`
- `delete_stale_records()`

Adding new connectors doesn't require modifying core business logic.

### RAG Workflow (LangGraph)
Configurable graph with nodes for:
1. Input validation
2. Tenant resolution
3. Assistant configuration lookup
4. Knowledge base selection
5. Query rewriting (optional)
6. Retrieval
7. Reranking (optional)
8. Context building
9. LLM call
10. Output validation
11. Citation attachment

### Zero-Touch Philosophy
After deployment, administrators can:
- ✅ Create/edit pages
- ✅ Configure branding
- ✅ Add AI models
- ✅ Create prompts
- ✅ Upload documents
- ✅ Configure connectors
- ✅ Manage users/permissions

Without touching a single line of Python code.

## Troubleshooting

### Database Issues

```bash
# Reset database (development only!)
rm db.sqlite3
python manage.py migrate
python manage.py setup_ai_cms
```

### Celery Not Working

```bash
# Check Redis connection
redis-cli ping

# Check Celery workers
celery -A config inspect active

# View Celery logs
celery -A config events
```

### Qdrant Connection Issues

```bash
# Check Qdrant health
curl http://localhost:6333/health

# Check collection status
curl http://localhost:6333/collections
```

## Documentation

- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Development roadmap
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System design
- [API_GUIDE.md](./docs/API_GUIDE.md) - REST API documentation
- [ADMIN_GUIDE.md](./docs/ADMIN_GUIDE.md) - Administrator instructions
- [CONNECTOR_GUIDE.md](./docs/CONNECTOR_GUIDE.md) - Adding new connectors
- [DEPLOYMENT.md](./docs/DEPLOYMENT.md) - Production deployment
- [SECURITY.md](./docs/SECURITY.md) - Security considerations

## Contributing

1. Create a feature branch
2. Make changes in an app
3. Run tests: `pytest`
4. Run linting: `black . && flake8 .`
5. Create pull request

## License

[Specify your license]

## Support

For issues or questions:
- Check [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)
- Review [KNOWN_LIMITATIONS.md](./docs/KNOWN_LIMITATIONS.md)
- Create an issue in the repository

## Roadmap

### Phase 2: CMS Page Types & Content
- [ ] StreamField blocks (heading, image, hero, CTA, cards, etc.)
- [ ] Branding configuration UI
- [ ] Navigation menu admin

### Phase 3: AI Provider Abstraction
- [ ] Provider registry
- [ ] Multi-provider support
- [ ] Credential management

### Phase 4-9: Full Implementation
See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for complete roadmap

---

Built with ❤️ for enterprise AI content management
