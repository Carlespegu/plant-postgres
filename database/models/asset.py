from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    BigInteger,
    SmallInteger,
    String,
    Text,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    func,
)
from App.db.base import Base


class AssetType(Base):
    __tablename__ = "asset_types"

    id = Column(SmallInteger, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class AssetStatus(Base):
    __tablename__ = "asset_statuses"

    id = Column(SmallInteger, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class RelationType(Base):
    __tablename__ = "relation_types"

    id = Column(SmallInteger, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class Asset(Base):
    __tablename__ = "assets"

    id = Column(BigInteger, primary_key=True)
    external_id = Column(String(120), nullable=False, unique=True)
    name = Column(String(150), nullable=False)

    asset_type_id = Column(SmallInteger, ForeignKey("asset_types.id"), nullable=False)
    status_id = Column(SmallInteger, ForeignKey("asset_statuses.id"), nullable=False)

    installation_id = Column(BigInteger, ForeignKey("installations.id", ondelete="CASCADE"), nullable=False)
    installation_group_id = Column(BigInteger, ForeignKey("installation_groups.id", ondelete="SET NULL"))
    parent_asset_id = Column(BigInteger, ForeignKey("assets.id", ondelete="SET NULL"))

    serial_number = Column(String(120))
    manufacturer = Column(String(120))
    model = Column(String(120))
    firmware_version = Column(String(80))
    description = Column(Text)
    notes = Column(Text)

    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    altitude_m = Column(Numeric(8, 2))

    installed_at = Column(DateTime(timezone=True))
    last_seen_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AssetRelation(Base):
    __tablename__ = "asset_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_asset_id",
            "target_asset_id",
            "relation_type_id",
            name="uq_asset_relations_source_target_type",
        ),
        CheckConstraint("source_asset_id <> target_asset_id", name="chk_asset_relations_source_target_diff"),
    )

    id = Column(BigInteger, primary_key=True)
    source_asset_id = Column(BigInteger, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    target_asset_id = Column(BigInteger, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    relation_type_id = Column(SmallInteger, ForeignKey("relation_types.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())