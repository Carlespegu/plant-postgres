from sqlalchemy import (
    Column,
    DateTime,
    BigInteger,
    SmallInteger,
    String,
    Text,
    Numeric,
    Integer,
    ForeignKey,
    UniqueConstraint,
    func,
)
from App.db.base import Base


class InstallationType(Base):
    __tablename__ = "installation_types"

    id = Column(SmallInteger, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class InstallationStatus(Base):
    __tablename__ = "installation_statuses"

    id = Column(SmallInteger, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class GroupStatus(Base):
    __tablename__ = "group_statuses"

    id = Column(SmallInteger, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class Installation(Base):
    __tablename__ = "installations"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    installation_type_id = Column(SmallInteger, ForeignKey("installation_types.id"))
    status_id = Column(SmallInteger, ForeignKey("installation_statuses.id"), nullable=False)

    name = Column(String(150), nullable=False)
    description = Column(Text)
    location_name = Column(String(255))
    address_line = Column(String(255))
    city = Column(String(120))
    region = Column(String(120))
    country = Column(String(120))
    postal_code = Column(String(30))
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    altitude_m = Column(Numeric(8, 2))
    timezone = Column(String(100))

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InstallationGroup(Base):
    __tablename__ = "installation_groups"
    __table_args__ = (
        UniqueConstraint("installation_id", "name", name="uq_installation_groups_installation_name"),
    )

    id = Column(BigInteger, primary_key=True)
    installation_id = Column(BigInteger, ForeignKey("installations.id", ondelete="CASCADE"), nullable=False)
    status_id = Column(SmallInteger, ForeignKey("group_statuses.id"))
    name = Column(String(150), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())