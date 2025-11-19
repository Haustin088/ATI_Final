from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSON
from .db import Base 

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    title = Column(String)
    url = Column(String, unique=True)
    published_at = Column(DateTime)
    content = Column(Text)
    authors = Column(JSON, default=[])
    images = Column(JSON, default=[])   

class Script(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer)
    draft = Column(Text)
    final = Column(Text)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="User")