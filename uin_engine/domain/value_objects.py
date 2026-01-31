from pydantic import BaseModel, Field, ConfigDict


class ImmutableValueObject(BaseModel):
    """
    A base class for value objects to ensure they are immutable.
    Value objects are compared by their values, not their identity.
    """
    model_config = ConfigDict(frozen=True)


class Position(ImmutableValueObject):
    """Represents a position in the game world, tied to a location."""
    location_id: str
    # Optional coordinates for more granular positioning within a location
    coordinates: tuple[int, int] | None = None


class KnowledgeEntry(ImmutableValueObject):
    """Represents a single piece of knowledge a character has about a fact."""
    fact_id: str
    certainty: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Certainty from 0.0 (complete doubt) to 1.0 (absolute certainty)"
    )


class Relationship(ImmutableValueObject):
    """
    Represents the feelings of one character towards another.
    This is a one-way relationship.
    """
    target_character_id: str
    affinity: float = Field(
        default=0.0,
        description="General positive/negative feeling. e.g., -1.0 (hate) to 1.0 (love)"
    )
    trust: float = Field(
        default=0.0,
        description="How much the character is trusted. e.g., 0.0 (no trust) to 1.0 (full trust)"
    )

