from sqlmodel import SQLModel, Field, Column, Relationship
from datetime import datetime, timezone
from pgvector.sqlalchemy import VECTOR
from uuid import UUID, uuid4
from typing import Optional

class users(SQLModel, table = True):
    id: str = Field(primary_key = True, default = None)
    password: str = Field(nullable = False)
    docs: list["docs"] = Relationship(back_populates = 'user', cascade_delete = True)

class docs(SQLModel, table = True):
    id: UUID = Field(primary_key = True, default_factory = uuid4)
    doc_name: str = Field(unique = True, nullable = False)
    uploaded_at: datetime = Field(default_factory = datetime.now)
    user_id: str = Field(foreign_key = "users.id")
    user: users = Relationship(back_populates = 'docs')
    chunks: list["chunks"] = Relationship(back_populates = 'doc',cascade_delete = True)
    chats: list["chats"] = Relationship(back_populates = 'doc', cascade_delete = True)

class chunks(SQLModel, table = True):
    id: UUID = Field(primary_key = True, default_factory = uuid4)
    doc_id: UUID = Field(foreign_key = "docs.id", )
    content: str = Field(nullable = False)
    embedding: list[float] = Field(sa_column = Column(VECTOR(384), nullable = False))
    doc: docs = Relationship(back_populates = 'chunks')

class chats(SQLModel, table = True):
    id: UUID = Field(primary_key = True, default_factory = uuid4)
    user_id: str = Field(foreign_key = "users.id")
    doc_id: UUID = Field(foreign_key = "docs.id")
    question_content: str = Field(nullable = False)
    question_embedding: list[float] = Field(sa_column = Column(VECTOR(384), nullable = True))
    response_content: str = Field(nullable = False)
    doc: docs = Relationship(back_populates = 'chats') 
    queried_at: datetime = Field(default_factory = datetime.now)
