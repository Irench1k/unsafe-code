# Django Basic Example

This is a basic Django application demonstrating common web application patterns and security vulnerabilities.

## Project Structure

The project follows a standardized structure that maintains Django best practices while providing a consistent interface across different Python frameworks:

```
myproject/          # Django project settings
├── __init__.py
├── settings.py     # Django settings
├── urls.py         # Main URL configuration
├── wsgi.py         # WSGI application
└── asgi.py         # ASGI application

myapp/              # Django application
├── __init__.py
├── admin.py        # Admin interface configuration
├── apps.py         # App configuration
├── models.py       # Data models
├── views.py        # View functions
├── urls.py         # App URL configuration
└── templates/      # HTML templates

app.py              # Standardized entry point (NEW!)
manage.py           # Django management commands
requirements.txt    # Python dependencies
Dockerfile          # Container configuration
```

## Running the Application

### Standardized Approach (Recommended)

This project now supports the standardized `python app.py` pattern used across all frameworks:

```bash
# Run the web server
python app.py

# Run with custom host/port
APP_HOST=127.0.0.1 APP_PORT=8080 python app.py

# Enable development auto-reload
DEV_RELOAD=1 python app.py
```

### Traditional Django Approach

All standard Django commands work as expected:

```bash
# Run the development server
python manage.py runserver

# Run with custom host/port
python manage.py runserver 127.0.0.1:8080

# Database operations
python manage.py migrate
python manage.py createsuperuser

# Shell access
python manage.py shell

# Run tests
python manage.py test
```

### Docker Deployment

```bash
# Build and run
docker build -t django-app .
docker run -p 8000:8000 django-app

# With environment variables
docker run -p 8000:8000 \
  -e APP_HOST=0.0.0.0 \
  -e APP_PORT=8000 \
  -e DEV_RELOAD=0 \
  django-app
```

## Environment Variables

The application respects these environment variables:

- `APP_HOST`: Server host (default: 0.0.0.0)
- `APP_PORT`: Server port (default: 8000)
- `DEV_RELOAD`: Enable auto-reload (default: 0)
- `DJANGO_SETTINGS_MODULE`: Django settings module (auto-configured)

## Key Features

- **Standardized Entry Point**: `app.py` provides a consistent interface across frameworks
- **Django Compatibility**: Full compatibility with Django's ecosystem and tooling
- **Environment Configuration**: Flexible configuration via environment variables
- **Production Ready**: Suitable for both development and production deployment

## Security Notes

This example intentionally contains security vulnerabilities for educational purposes:

- SQL injection vulnerabilities in views
- XSS vulnerabilities in template rendering
- CSRF protection disabled in some views
- Insecure direct object references

**Do not use this code in production!**

## Development Workflow

1. **Standard Development**: Use `python manage.py runserver` for typical Django development
2. **Standardized Testing**: Use `python app.py` to test the standardized entry point
3. **Docker Testing**: Use Docker to test the production-like environment
4. **Management Commands**: All Django management commands work with both approaches

The `app.py` file acts as a bridge between our standardized project structure and Django's standard tooling, making it easy to maintain consistency across different frameworks while preserving Django's powerful ecosystem.
