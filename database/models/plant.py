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
    func,
)
from App.db.base import Base


class PlantType(Base):
    __tablename__ = "plant_types"

    id = Column(SmallInteger, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class PotType(Base):
    __tablename__ = "pot_types"

    id = Column(SmallInteger, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class PlantSpecies(Base):
    __tablename__ = "plant_species"
    __table_args__ = (
        CheckConstraint(
            "ideal_temp_min_c IS NULL OR ideal_temp_max_c IS NULL OR ideal_temp_min_c <= ideal_temp_max_c",
            name="chk_plant_species_temp_range",
        ),
        CheckConstraint(
            "ideal_soil_moisture_min IS NULL OR ideal_soil_moisture_max IS NULL OR ideal_soil_moisture_min <= ideal_soil_moisture_max",
            name="chk_plant_species_soil_range",
        ),
        CheckConstraint(
            "ideal_light_min IS NULL OR ideal_light_max IS NULL OR ideal_light_min <= ideal_light_max",
            name="chk_plant_species_light_range",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    common_name = Column(String(150), nullable=False)
    scientific_name = Column(String(200))

    plant_type_id = Column(SmallInteger, ForeignKey("plant_types.id"))
    default_pot_type_id = Column(SmallInteger, ForeignKey("pot_types.id"))

    size_category = Column(String(50))
    sunlight_level = Column(String(50))
    watering_level = Column(String(50))
    humidity_level = Column(String(50))

    ideal_temp_min_c = Column(Numeric(5, 2))
    ideal_temp_max_c = Column(Numeric(5, 2))
    ideal_soil_moisture_min = Column(Numeric(5, 2))
    ideal_soil_moisture_max = Column(Numeric(5, 2))
    ideal_light_min = Column(SmallInteger)
    ideal_light_max = Column(SmallInteger)

    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Plant(Base):
    __tablename__ = "plants"
    __table_args__ = (
        CheckConstraint(
            "installation_id IS NOT NULL OR installation_group_id IS NOT NULL",
            name="chk_plants_location",
        ),
        CheckConstraint(
            "custom_temp_min_c IS NULL OR custom_temp_max_c IS NULL OR custom_temp_min_c <= custom_temp_max_c",
            name="chk_plants_temp_range",
        ),
        CheckConstraint(
            "custom_soil_moisture_min IS NULL OR custom_soil_moisture_max IS NULL OR custom_soil_moisture_min <= custom_soil_moisture_max",
            name="chk_plants_soil_range",
        ),
        CheckConstraint(
            "custom_light_min IS NULL OR custom_light_max IS NULL OR custom_light_min <= custom_light_max",
            name="chk_plants_light_range",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    installation_id = Column(BigInteger, ForeignKey("installations.id", ondelete="CASCADE"))
    installation_group_id = Column(BigInteger, ForeignKey("installation_groups.id", ondelete="SET NULL"))
    plant_species_id = Column(BigInteger, ForeignKey("plant_species.id"), nullable=False)

    name = Column(String(150), nullable=False)
    nickname = Column(String(150))
    pot_type_id = Column(SmallInteger, ForeignKey("pot_types.id"))

    planted_at = Column(DateTime(timezone=True))
    acquired_at = Column(DateTime(timezone=True))

    custom_temp_min_c = Column(Numeric(5, 2))
    custom_temp_max_c = Column(Numeric(5, 2))
    custom_soil_moisture_min = Column(Numeric(5, 2))
    custom_soil_moisture_max = Column(Numeric(5, 2))
    custom_light_min = Column(SmallInteger)
    custom_light_max = Column(SmallInteger)

    status = Column(String(50))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())