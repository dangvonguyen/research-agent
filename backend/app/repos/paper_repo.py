from app.models import Paper, PaperCreate, PaperUpdate

from .base_repo import BaseRepository


class PaperRepository(BaseRepository[Paper, PaperCreate, PaperUpdate]):
    """Repository for paper data access."""

    collection_name = "papers"
    model_class = Paper
