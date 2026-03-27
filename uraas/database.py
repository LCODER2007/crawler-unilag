from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from uraas.config import config

Base = declarative_base()

# Many-to-Many Association Tables
item_authors = Table('item_authors', Base.metadata,
    Column('item_id', Integer, ForeignKey('items.id', ondelete="CASCADE"), primary_key=True),
    Column('author_id', Integer, ForeignKey('authors.id', ondelete="CASCADE"), primary_key=True)
)

item_collections = Table('item_collections', Base.metadata,
    Column('item_id', Integer, ForeignKey('items.id', ondelete="CASCADE"), primary_key=True),
    Column('collection_id', Integer, ForeignKey('collections.id', ondelete="CASCADE"), primary_key=True),
    Column('confidence_score', Float, default=1.0)
)

class Community(Base):
    __tablename__ = 'communities'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    
    collections = relationship('Collection', back_populates='community')

class Collection(Base):
    __tablename__ = 'collections'
    id = Column(Integer, primary_key=True)
    community_id = Column(Integer, ForeignKey('communities.id'), nullable=False)
    name = Column(String(255), unique=True, nullable=False)
    email_domains = Column(Text) # Comma-separated list for matching
    keywords = Column(Text) # Comma-separated keyword list
    
    community = relationship('Community', back_populates='collections')
    items = relationship('Item', secondary=item_collections, back_populates='collections')

class Author(Base):
    __tablename__ = 'authors'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    profile_url = Column(String(512))
    
    items = relationship('Item', secondary=item_authors, back_populates='authors')

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    title = Column(String(512), nullable=False)
    abstract = Column(Text)
    doi = Column(String(255), unique=True)
    publication_date = Column(DateTime)
    url = Column(String(512), unique=True)
    source_repository = Column(String(100))
    pdf_url = Column(String(512))
    
    # DSpace Dublin Core Metadata Schema Support
    dc_title = Column(String(512))
    dc_date_issued = Column(String(50))
    dc_identifier_uri = Column(String(512))
    dc_identifier_doi = Column(String(255))       # dc.identifier.doi
    dc_description_provenance = Column(Text)       # dc.description.provenance
    dc_rights = Column(String(255), default='info:eu-repo/semantics/restrictedAccess')  # dc.rights
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    authors = relationship('Author', secondary=item_authors, back_populates='items')
    collections = relationship('Collection', secondary=item_collections, back_populates='items')
    files = relationship('File', back_populates='item', cascade="all, delete-orphan")

class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id', ondelete="CASCADE"), nullable=False)
    file_path = Column(String(512), nullable=False)
    sha256_hash = Column(String(128))
    access_policy = Column(String(50), default="Private") # Copyright Safe Mode Active
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    
    item = relationship('Item', back_populates='files')

class CrawlJob(Base):
    __tablename__ = 'crawl_jobs'
    id = Column(Integer, primary_key=True)
    source_name = Column(String(100), nullable=False)
    status = Column(String(50), default="PENDING")
    items_scraped = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)

# Database setup and connection
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
