from pydantic import BaseModel, ConfigDict, computed_field
from typing import Optional


class RaceCategoryBase(BaseModel):
    title: str
    code: str
    distance_km: float
    price_inr: float
    max_capacity: int
    bib_prefix: str
    min_age: int
    start_time: str
    is_active: bool = True


class RaceCategoryResponse(RaceCategoryBase):
    id: str
    current_count: int

    @computed_field
    @property
    def slots_remaining(self) -> int:
        return max(0, self.max_capacity - self.current_count)

    model_config = ConfigDict(from_attributes=True)
