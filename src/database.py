from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

_base_dir = Path(__file__).resolve().parent.parent

db_path = _base_dir / "data" / "metadata" / "documents.db"
db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{db_path}")

Base = declarative_base()

class DocumentVersion(Base):
    __tablename__ = 'document_versions'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    category = Column(String)
    file_format = Column('format', String)
    sha256 = Column(String)
    local_path = Column(String)
    source_url = Column(String)
    downloaded_at = Column(DateTime, default=datetime.utcnow)

# Lazy table creation
def init_db():
    Base.metadata.create_all(engine)

init_db()

Session = sessionmaker(bind=engine)