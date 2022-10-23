from sqlalchemy import Column, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Raffle(Base):
    __tablename__ = "raffles"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False, unique=True)

    def __repr__(self):
        return f"Raffle(id={self.id!r}, guild_id={self.guild_id!r}, message_id={self.message_id!r})"

class Entry(Base):
    __tablename__ = "raffle_entries"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)

    def __repr__(self):
        return f"Entry(id={self.id!r}, guild_id={self.guild_id!r}, message_id={self.message_id!r}, user_id={self.user_id!r})"

class Win(Base):
    __tablename__ = "past_wins"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)

    def __repr__(self):
        return f"Win(id={self.id!r}, guild_id={self.guild_id!r}, message_id={self.message_id!r}, user_id={self.user_id!r})"

class EligibleRole(Base):
    __tablename__ = "eligible_roles"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False)
    role_id = Column(Integer, nullable=False, unique=True)

    def __repr__(self):
        return f"EligibleRole(id={self.id!r}, guild_id={self.guild_id!r}, role_id={self.role_id!r})"
