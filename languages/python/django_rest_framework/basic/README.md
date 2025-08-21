# Django REST Framework Basic Example

A basic Django REST Framework application demonstrating common web API patterns and security vulnerabilities. Built with [Django REST Framework](https://www.django-rest-framework.org/).

## Quick Start

```bash
cd languages/python/django_rest_framework/basic
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

## Project Structure

This example follows Django's standard project structure:

```
myproject/          # Django project settings
├── settings.py     # Django settings
├── urls.py         # Main URL configuration
├── wsgi.py         # WSGI application
└── asgi.py         # ASGI application

myapp/              # Django application
├── models.py       # Data models
├── views.py        # API views
├── urls.py         # App URL configuration
└── tests.py        # Test cases

app.py              # Standardized entry point
manage.py           # Django management commands
requirements.txt    # Python dependencies
Dockerfile          # Container configuration
```

The `app.py` file provides a consistent interface across all frameworks while maintaining full Django compatibility.
