import logging

from pymongo import IndexModel

from app.models import Paper, PaperCreate, PaperUpdate

from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class PaperRepository(BaseRepository[Paper, PaperCreate, PaperUpdate]):
    """Repository for paper data access."""

    collection_name = "papers"
    model_class = Paper
    indexes = [
        IndexModel([("job_id", 1)], name="paper_job_id"),
        IndexModel([("source", 1)], name="paper_source"),
        IndexModel([("source_id", 1)], name="paper_source_id"),
    ]
