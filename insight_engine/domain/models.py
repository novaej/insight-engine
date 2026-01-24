import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_profile: Mapped[dict] = mapped_column(JSON, nullable=False)
    assets: Mapped[dict] = mapped_column(JSON, nullable=False)
    overall_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InsightRecord(Base):
    __tablename__ = "insights"

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
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
