# AI CMS - Quick Start Guide

## 🚀 Fastest Way to Get Running (5 minutes)

### Option 1: Automated Setup (Recommended)

```bash
cd /home/Nandprakash.Goutam1/Downloads/ai-cms
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

Then:
```bash
python manage.py createsuperuser
python manage.py runserver
```

Visit: `http://localhost:8000/admin`

### Option 2: Manual Setup

```bash
# Navigate to project
cd /home/Nandprakash.Goutam1/Downloads/ai-cms

# Activate virtual environment
source .venv/bin/activate

# Project is already configured - just create a superuser and run!
python manage.py createsuperuser
python manage.py runserver
```

Visit: `http://localhost:8000/admin`

## ✅ What's Ready Now

- ✅ Django + Wagtail CMS
- ✅ 16 Apps (core, tenants, ai_providers, prompts, knowledge, ingestion, etc.)
- ✅ Database (SQLite for dev, PostgreSQL ready)
- ✅ Admin Interface
- ✅ Environment Configuration
- ✅ Celery Background Jobs (optional)
- ✅ Docker Infrastructure (optional)

## 🎯 Next Steps

### 1. Create Admin User
```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

### 2. Start Development Server
```bash
python manage.py runserver
```

### 3. Access Admin
Open browser to: `http://localhost:8000/admin`

### 4. Login
Use credentials from step 1

## 📚 Key Documentation

- **README.md** - Complete feature overview and setup
- **IMPLEMENTATION_PLAN.md** - 9-phase development roadmap
- **PHASE_1_COMPLETION.md** - Phase 1 summary
- **TASKS.md** - Task checklist with progress

## ⚙️ Configuration

### Environment Variables (.env)
Already created and ready. For custom settings:

```bash
# Edit .env file
nano .env

# Key variables:
DJANGO_DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
DJANGO_SECRET_KEY=your-secret-here
```

### Database
- **Development**: SQLite (db.sqlite3) - works out of the box
- **Production**: Configure DATABASE_URL for PostgreSQL

```bash
# Switch to PostgreSQL (requires docker-compose)
docker-compose up -d postgres redis qdrant
# Update .env:
# DATABASE_URL=postgres://ai_cms_user:ai_cms_password@localhost:5432/ai_cms
```

## 🔧 Optional: Background Jobs (Celery)

Terminal 1:
```bash
python manage.py runserver
```

Terminal 2:
```bash
celery -A config worker --loglevel=info
```

Terminal 3 (if using scheduling):
```bash
celery -A config beat --loglevel=info
```

## 🐳 Optional: Docker Infrastructure

Start all services (PostgreSQL, Redis, Qdrant):
```bash
docker-compose up -d
```

Update .env to use Docker services:
```bash
DATABASE_URL=postgres://ai_cms_user:ai_cms_password@localhost:5432/ai_cms
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=qdrant-api-key
```

Re-run migrations:
```bash
python manage.py migrate
```

Stop services:
```bash
docker-compose down
```

## 🧪 Testing

Run tests:
```bash
pytest
```

With coverage:
```bash
pytest --cov=apps
```

## 📋 Project Structure Quick Reference

```
ai_cms/
├── config/              # Django settings
├── apps/                # 16 domain apps
│   ├── core/           # Core utilities
│   ├── tenants/        # Multi-tenancy
│   ├── branding/       # Site branding
│   ├── navigation/     # Menus
│   ├── ai_providers/   # LLM integrations
│   ├── prompts/        # Prompt templates
│   ├── knowledge/      # Knowledge bases
│   ├── ingestion/      # Document processing
│   ├── connectors/     # Data connectors
│   ├── retrieval/      # RAG service
│   ├── workflows/      # Orchestration
│   ├── conversations/  # Chat system
│   ├── audit/          # Logging
│   ├── observability/  # Metrics
│   └── api/            # REST API
├── home/               # Wagtail home
├── search/             # Wagtail search
├── templates/          # Global templates
├── static/             # CSS, JS
└── media/              # Uploads
```

## 🆘 Troubleshooting

### Django won't start
```bash
python manage.py check
# Shows any configuration issues
```

### Database issues
```bash
# Reset database (dev only!)
rm db.sqlite3
python manage.py migrate
python manage.py setup_ai_cms
```

### Port already in use
```bash
python manage.py runserver 127.0.0.1:8001
# Or kill the process using port 8000
lsof -i :8000
```

### Virtual environment issues
```bash
# Recreate it
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt
```

## 📞 What's Next?

After starting the server and accessing admin:

1. **Create Pages**
   - Go to Pages section
   - Create new page
   - Add content using blocks

2. **Configure Branding**
   - Settings → Branding
   - Add logo, colors, fonts

3. **Setup Navigation**
   - Settings → Navigation
   - Create menus
   - Add links

4. **Add AI Provider** (Phase 2+)
   - Configure OpenAI, Gemini, etc.
   - Test connections
   - Create prompts

5. **Upload Documents** (Phase 5+)
   - Create Knowledge Base
   - Upload Excel/PDF
   - Configure extraction

## 🎓 Learning Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Wagtail Documentation](https://docs.wagtail.org/)
- [LangChain Documentation](https://docs.langchain.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)

## 💡 Tips

- Use `python manage.py shell` for interactive debugging
- Use `python manage.py dbshell` to interact with database
- Use `docker-compose logs -f` to see service logs
- Use `black` to format code: `black apps/`
- Use `pytest` to run tests: `pytest`

---

**Welcome to AI CMS!** 🎉

For detailed information, see README.md
