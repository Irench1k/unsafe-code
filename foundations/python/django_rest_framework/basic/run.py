#!/usr/bin/env python
"""
Django REST Framework application entry point that provides a standard interface
while maintaining full Django compatibility and best practices.

This file serves as a bridge between our standardized project structure
and Django's standard tooling. It can be used in two ways:

1. Direct execution: python app.py (for Docker/standardized deployment)
2. Django management: python manage.py runserver (for development/Django workflows)

The app.py approach is common in Django production deployments and
maintains full compatibility with Django's ecosystem.
"""
import os
import sys
from django.core.management import execute_from_command_line


def main():
    """Main entry point for the Django REST Framework application."""
    # Get configuration from environment variables with sensible defaults
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))
    # Enable Django's auto-reloader in development when requested
    debug = os.environ.get("DEV_RELOAD", "0") == "1"
    
    # Set Django settings module if not already set
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
    
    # Check if we're being run directly (python app.py) or via Django management
    if len(sys.argv) == 1:
        # Direct execution: simulate 'python manage.py runserver'
        argv = [
            "manage.py",
            "runserver",
            f"{host}:{port}"
        ]
        
        # Disable auto-reload unless in development mode
        if not debug:
            argv.append("--noreload")
        
        # Execute the Django command
        execute_from_command_line(argv)
    else:
        # Django management command execution (e.g., python app.py migrate)
        execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
