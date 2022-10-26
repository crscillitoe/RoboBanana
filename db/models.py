from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Raffle(Base):
    __tablename__ = "raffles"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False, unique=True)
    entries = relationship("RaffleEntry", back_populates="raffle")

    def __repr__(self):
        return f"Raffle(id={self.id!r}, guild_id={self.guild_id!r}, message_id={self.message_id!r})"

class RaffleEntry(Base):
    __tablename__ = "raffle_entries"

    id = Column(Integer, primary_key=True)
    raffle_id = Column(Integer, ForeignKey("raffles.id"))
    guild_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    raffle = relationship("Raffle", back_populates="entries")

    def __repr__(self):
        return f"RaffleEntry(id={self.id!r}, raffle_id={self.raffle_id!r}, guild_id={self.guild_id!r}, message_id={self.message_id!r}, user_id={self.user_id!r})"

class RoleModifier(Base):
    __tablename__ = "role_modifiers"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, nullable=False)
    role_id = Column(Integer, nullable=True, unique=True)
    role_name = Column(String, nullable=True)

    def __repr__(self):
        return f"RoleModifier(id={self.id!r}, guild_id={self.guild_id!r}, role_id={self.role_id!r})"