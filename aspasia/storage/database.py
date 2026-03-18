"""Database abstraction layer for Aspasia."""

import logging
from typing import Optional
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()


class ConversationRecord(Base):
    """Database model for conversation records."""

    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    role = Column(String)  # "user" or "assistant"
    content = Column(Text)
    metadata = Column(JSON)
    timestamp = Column(DateTime, default=datetime.now, index=True)


class UserRecord(Base):
    """Database model for user data."""

    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    last_interaction = Column(DateTime)
    preferences = Column(JSON)
    facts = Column(JSON)


class Database:
    """Database connection and operations."""

    def __init__(self, database_url: str):
        """
        Initialize database.

        Args:
            database_url: Database connection URL
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.url = database_url

    def init_db(self) -> None:
        """Initialize database schema."""
        Base.metadata.create_all(self.engine)
        logger.info("Database initialized")

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def store_message(
        self, user_id: str, role: str, content: str, metadata: dict = None
    ) -> None:
        """Store a message in the database."""
        session = self.get_session()
        try:
            record = ConversationRecord(
                id=f"{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                role=role,
                content=content,
                metadata=metadata or {},
            )
            session.add(record)
            session.commit()
            logger.debug(f"Stored message for {user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing message: {str(e)}")
            raise
        finally:
            session.close()

    def get_user_messages(
        self, user_id: str, limit: int = 100
    ) -> list[dict]:
        """Get messages for a user."""
        session = self.get_session()
        try:
            records = (
                session.query(ConversationRecord)
                .filter(ConversationRecord.user_id == user_id)
                .order_by(ConversationRecord.timestamp.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "role": r.role,
                    "content": r.content,
                    "timestamp": r.timestamp.isoformat(),
                    "metadata": r.metadata,
                }
                for r in reversed(records)
            ]
        finally:
            session.close()

    def store_user(self, user_id: str, preferences: dict = None, facts: dict = None):
        """Store or update user record."""
        session = self.get_session()
        try:
            user = session.query(UserRecord).filter_by(user_id=user_id).first()

            if user:
                user.last_interaction = datetime.now()
                if preferences:
                    user.preferences = preferences
                if facts:
                    user.facts = facts
            else:
                user = UserRecord(
                    user_id=user_id,
                    preferences=preferences or {},
                    facts=facts or {},
                )
                session.add(user)

            session.commit()
            logger.debug(f"Stored user {user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing user: {str(e)}")
            raise
        finally:
            session.close()

    def get_user(self, user_id: str) -> Optional[dict]:
        """Get user record."""
        session = self.get_session()
        try:
            user = session.query(UserRecord).filter_by(user_id=user_id).first()
            if user:
                return {
                    "user_id": user.user_id,
                    "created_at": user.created_at.isoformat(),
                    "last_interaction": user.last_interaction.isoformat()
                    if user.last_interaction
                    else None,
                    "preferences": user.preferences or {},
                    "facts": user.facts or {},
                }
            return None
        finally:
            session.close()

    def delete_user_messages(self, user_id: str) -> None:
        """Delete all messages for a user."""
        session = self.get_session()
        try:
            session.query(ConversationRecord).filter_by(user_id=user_id).delete()
            session.commit()
            logger.info(f"Deleted messages for user {user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting messages: {str(e)}")
            raise
        finally:
            session.close()
