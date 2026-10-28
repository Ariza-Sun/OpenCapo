from typing import Self

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """Immutable, strictly-shaped base for every serialized object."""

    # strict: no silent coercion ("3" -> 3, true -> 1); enums and tuples must be
    # passed as such from Python, while JSON input uses plain values and arrays.
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, allow_inf_nan=False)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, data: str | bytes) -> Self:
        return cls.model_validate_json(data)
