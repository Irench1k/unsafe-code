# Flask Applications

[Flask](https://flask.palletsprojects.com/) is a lightweight WSGI web application framework in Python. It's designed to be simple and easy to use, making it a popular choice for building web applications and APIs.

## Directory Structure

```
flask/
├── README.md
├── basic/
│   ├── app.py              # Main application file
│   ├── compose.dev.yml     # Docker compose file for development
│   ├── compose.yml         # Docker compose file for production
│   ├── Dockerfile         # Docker configuration
│   ├── metadata.yml       # Application metadata
│   └── requirements.txt   # Python dependencies
├── routing-multifile-register/
│   ├── compose.dev.yml
│   ├── compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py
│   └── webapp/            # Application with manual route registration
├── routing-multifile-autodiscovery/
│   ├── compose.dev.yml
│   ├── compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py
│   └── webapp/            # Application with automatic route discovery
└── blueprints/
    └── README.md          # Blueprint patterns guide (no runnable code)
```

## Examples Overview

### [basic](basic/)
A minimal Flask application demonstrating fundamental concepts and clean coding practices. This serves as the foundation for understanding Flask's core functionality.

### [routing-multifile-register](routing-multifile-register/)
Demonstrates manual route organization across multiple files using explicit registration patterns. Shows how to structure larger applications with clear, maintainable code organization.

### [routing-multifile-autodiscovery](routing-multifile-autodiscovery/)
Showcases automated route discovery and registration using convention-based patterns. Demonstrates advanced architectural patterns for scalable application structure.

### [blueprints](blueprints/)
Comprehensive guide to Flask blueprints for hierarchical application organization. Covers blueprint creation, nested registration, and patterns for structuring large applications. References working examples in the vulnerabilities section.

## Getting Started

### Running Any Example

1. Navigate to the desired example directory:
   ```bash
   cd foundations/python/flask/basic
   ```

2. Using Docker (Recommended):
   ```bash
   # For development
   docker compose -f compose.dev.yml up

   # For production
   docker compose up
   ```

3. Without Docker (Local Development):
   ```bash
   # Create and activate a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Run the application
   python app.py  # or python run.py for routing examples
   ```

Applications will typically be available at `http://localhost:5000`.

## Learning Path

We recommend exploring these examples in this order:

1. **Start with `basic`** - Understand Flask fundamentals and clean application structure
2. **Explore `routing-multifile-register`** - Learn manual route organization patterns
3. **Study `routing-multifile-autodiscovery`** - Understand automated, convention-based patterns
4. **Review `blueprints`** - Learn blueprint patterns for hierarchical, modular organization

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask Best Practices](https://flask.palletsprojects.com/en/latest/patterns/)
- [Flask Application Factories](https://flask.palletsprojects.com/en/latest/patterns/appfactories/)