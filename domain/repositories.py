from abc import ABC, abstractmethod
from typing import List, Literal, Optional
from domain.models import CoffeeProductDomain

class ICoffeeRepository(ABC):
    @abstractmethod
    def get_cheapest_products(
        self, 
        sort_by: Literal["kilo", "unit"] = "kilo", 
        limit: int = 10, 
        only_available: bool = True,
        store_name: Optional[str] = None,
        min_weight_g: Optional[int] = None,
        max_weight_g: Optional[int] = None,
        search_query: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> List[CoffeeProductDomain]:
        pass

    @abstractmethod
    def count_cheapest_products(
        self,
        sort_by: Literal["kilo", "unit"] = "kilo",
        only_available: bool = True,
        store_name: Optional[str] = None,
        min_weight_g: Optional[int] = None,
        max_weight_g: Optional[int] = None,
        search_query: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> int:
        pass
