import os

from flask import Blueprint

from .db import ensure_schema, make_engine_for_schema, make_session
from .models import Base
#from .seed import seed
from .routes import bp

SCHEMA = "R05"

def register(app: Blueprint) -> None:
    """
    Register blueprint and (optionally) auto-init schema/tables/seed for this example.
    This file depends only on this example's own modules.
    """
    app.register_blueprint(bp)

    if os.getenv("AUTO_INIT_EXAMPLES", "0") != "1":
        return

    # Create schema, create tables into that schema, seed demo data
    ensure_schema()
    engine = make_engine_for_schema()
    Base.metadata.create_all(engine)
#    session = make_session()
#    try:
#        #seed(session)
#    finally:
#        session.close()
#