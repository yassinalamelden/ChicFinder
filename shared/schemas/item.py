from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ClothingItem:
    """
    Data model representing a single fashion item.
    """
    id: str
    category: str
    sub_category: str
    color: str
    style: str
    image_url: str
    brand: Optional[str] = None
    price: Optional[float] = None

@dataclass
class Recommendation:
    """
    Metadata for a group of recommended items based on a query.
    """
    query_item: dict # {type, color, style}
    suggestions: List[ClothingItem] = field(default_factory=list)
