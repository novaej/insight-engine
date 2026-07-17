import datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # pbkdf2$<iterations>$<salt-hex>$<hash-hex>; None for the default dev user
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # SHA-256 hex of the bearer token; rotated on each login
    api_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_profile: Mapped[dict] = mapped_column(JSON, nullable=False)
    overall_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Position(Base):
    """One purchase lot; a ticker may have several lots at different prices."""

    __tablename__ = "positions"
    __table_args__ = (Index("ix_positions_portfolio_ticker", "portfolio_id", "ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    purchase_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InsightRecord(Base):
    __tablename__ = "insights"
    __table_args__ = (
        Index("ix_insights_portfolio_ticker_created", "portfolio_id", "ticker", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    asset_state: Mapped[str] = mapped_column(String(30), nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=True)
    horizon: Mapped[str] = mapped_column(String(20), nullable=False)
    scenario: Mapped[str] = mapped_column(Text, nullable=True)
    risks: Mapped[dict] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    portfolio_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alternatives: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
