"""
Legacy MongoDB repository package.

All application data (papers, crawlers, conversations) now uses Postgres via
SQLAlchemy models and ``app.db.queries.*`` helpers. This package is kept only
so that old imports like ``import app.repos`` do not fail.
"""

__all__: list[str] = []
