# AI CMS Implementation Plan

## Overview

Building a production-oriented, modular, WordPress-like AI CMS using Python, Django, Wagtail CMS, LangChain, LangGraph, and Qdrant.

**Philosophy**: Zero-touch code after initial deployment. Administrators configure almost everything through Wagtail admin interface.

## Technical Stack

- **Python**: 3.12+
- **Framework**: Django 5.x + Wagtail CMS
- **API**: Django REST Framework
- **Database**: PostgreSQL (production), SQLite (local dev)
- **Vector DB**: Qdrant with qdrant-client
- **LLM Integration**: LangChain, LangGraph
- **Background Jobs**: Celery + Redis
- **File Processing**: pandas, openpyxl, BeautifulSoup, pypdf, python-docx
- **Logging**: structlog
- **Testing**: pytest, pytest-django
- **Environment**: django-environ

## Project Structure

```
ai_cms/
├── manage.py
├── .env.example
├── .gitignore
├── README.md
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py
├── apps/
│   ├── core/
│   ├── cms/
│   ├── accounts/
│   ├── tenants/
│   ├── branding/
│   ├── navigation/
│   ├── ai_providers/
│   ├── prompts/
│   ├── knowledge/
│   ├── ingestion/
│   ├── connectors/
│   ├── retrieval/
│   ├── workflows/
│   ├── conversations/
│   ├── audit/
│   └── observability/
├── templates/
├── static/
├── media/
├── tests/
├── scripts/
│   ├── bootstrap.sh
│   ├── run_dev.sh
│   ├── run_worker.sh
│   ├── run_beat.sh
│   └── test.sh
├── docs/
└── docker-compose.yml
```

## Implementation Phases

### Phase 1: Project Setup & Django Scaffolding
- Create `.venv` and install base dependencies
- Scaffold Django/Wagtail project
- Split settings (base, dev, production)
- Configure environment variables
- Create base templates
- Create home page
- Run checks and tests

### Phase 2: CMS Page Types & Core Content
- Page types (Home, Standard, Landing, Chat, Knowledge Base)
- StreamField blocks (heading, rich text, image, hero, CTA, cards, etc.)
- Branding configuration (logo, colors, fonts)
- Navigation menus
- Wagtail snippets and settings
- Roles and permissions
- Setup management command
- Unit tests

### Phase 3: AI Provider Abstraction
- Tenant abstraction layer
- AI provider registry and factory
- LLM model configuration management
- Embedding model configuration
- Provider test actions in admin
- Secret handling and masking
- Multi-provider support (OpenAI, Gemini, Groq, Ollama, local)
- Configuration validation
- Tests

### Phase 4: Qdrant Integration
- Qdrant connection management
- Knowledge base models
- Collection creation and validation
- Qdrant repository/service interface
- Collection statistics and inspection
- Tenant isolation for collections
- Admin actions for collection management
- Tests

### Phase 5: Document Ingestion
- Data source and uploaded document models
- Ingestion job tracking
- Excel/CSV mapping and preview
- Document extraction (PDF, DOCX, TXT, MD, HTML)
- Chunking and text normalization
- Duplicate detection and checksums
- Celery background processing
- Progress tracking
- Error handling and retry
- Tests

### Phase 6: Connector Framework
- Abstract connector interface
- Jira connector with REST API integration
- Confluence connector with REST API integration
- Connector registry
- Preview, sync, incremental sync
- Scheduled synchronization
- Stale data cleanup
- Rate limiting and retry
- Tests

### Phase 7: RAG Workflow & Prompt Management
- Prompt template registry
- Prompt versioning and approval
- LangChain document abstractions
- LangGraph RAG workflow
- Query rewriting
- Retrieval and reranking
- Citation generation
- Fallback behaviors
- Output validation
- Tests

### Phase 8: Public AI Assistant & Chat
- AI assistant configuration
- Conversation and message models
- Chat API endpoints
- Streaming support
- Session management
- Citation display
- Source panel
- Throttling and security
- Public page with UI
- Tests

### Phase 9: Admin Experience & Observability
- Custom admin dashboard
- Health and readiness endpoints
- Audit event logging
- Structured application logging
- Request correlation IDs
- Ingestion and sync monitoring
- Error summaries
- Safe metrics hooks
- Complete documentation
- Final security review

## Success Criteria

- ✅ Project starts with `.venv`
- ✅ `python manage.py check` passes
- ✅ Migrations apply successfully
- ✅ Tests pass
- ✅ Wagtail admin login works
- ✅ Create and publish content pages
- ✅ Configure AI provider without code changes
- ✅ Configure Qdrant and knowledge base
- ✅ Upload and ingest Excel files
- ✅ Jira/Confluence connectors configured
- ✅ Public chat page returns RAG-grounded responses
- ✅ No secrets in admin/logs
- ✅ All configuration via UI

## Key Architectural Decisions

1. **Multi-tenancy**: All models include tenant context
2. **Provider Abstraction**: Registry pattern for LLM/embedding providers
3. **Connector Framework**: Abstract contract allowing extensibility
4. **Configuration Philosophy**: Database-driven, admin-editable, never code-driven
5. **Background Jobs**: Celery for all long-running operations
6. **API Design**: Versioned REST endpoints with permission checks
7. **Security**: Comprehensive validation, no secrets in logs/UI
8. **Testing**: Mocks for external services, fixtures for test data

## Dependencies Management

- Requirements split by environment (base, dev, production)
- Pinned versions for reproducibility
- Regular security audits planned
- No eval/exec of admin-entered code
