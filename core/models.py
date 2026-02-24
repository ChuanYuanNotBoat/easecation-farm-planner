
from dataclasses import dataclass
from typing import Optional

@dataclass
class Crop:
    name: str
    growth_time: float
    expected_yield: float
    sell_price: float
    seed_cost: float
    exp_per_unit: Optional[float] = None
