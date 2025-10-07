# Flask Applications

[Flask](https://flask.palletsprojects.com/) is a lightweight WSGI web application framework in Python. It's designed to be simple and easy to use, making it a popular choice for building web applications and APIs.

## Directory Structure

```
flask/
├── README.md
└── basic/
    ├── app.py              # Main application file
    ├── compose.dev.yml     # Docker compose file for development
    ├── compose.yml         # Docker compose file for production
    ├── Dockerfile         # Docker configuration
    ├── metadata.yml       # Application metadata
    ├── requirements.txt   # Python dependencies
    └── __pycache__/      # Python bytecode cache
└── blueprint/
```

## Getting Started

The `basic` directory contains a minimal Flask application that demonstrates fundamental concepts and potential security considerations.

### Running the Application

1. Navigate to the basic directory:

   ```bash
   cd languages/python/flask/basic
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
   # Create and activate a virtual environment (optional but recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Run the application
   python app.py
   ```

The application will be available at `http://localhost:5000`.

## How to navigate
- [Inconsistent Interpretation (ii)](r01_ii/README.md) - Different parts of the code interpret the same input in incompatible ways.
- [Policy Composition and Precedence](r02_policy_composition_and_precedence/README.md) - Multiple guards combine so that the weakest one wins.
- [Trust Boundary Errors](trust_boundary_errors/README.md) - We believe headers or hosts that should only be accepted from trusted proxies.
- [Cross-Component Semantics](cross_component_semantics/README.md) - Proxies, CDNs, and Flask disagree about what the request actually contains.
- [Unsafe Defaults and Misconfiguration](unsafe_defaults_and_misconfiguration/README.md) - Development settings and sample secrets that leak into production.
- [Type Coercion](type_coercion/README.md) - Implicit casting changes the meaning of security checks.
- [Temporal Inconsistency](temporal_inconsistency/README.md) - Time-of-check versus time-of-use, race conditions, and replay issues.


## Security Considerations

This Flask application is part of the Unsafe Code Lab project, designed to demonstrate various security concepts and potential vulnerabilities. Please refer to the main project README for more information about the security research aspects.

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask Security Considerations](https://flask.palletsprojects.com/en/latest/security/)
- [Flask Extension Registry](https://flask.palletsprojects.com/en/latest/extensions/)
