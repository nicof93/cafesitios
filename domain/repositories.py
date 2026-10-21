from abc import ABC, abstractmethod
from typing import List, Literal, Optional
from domain.models import CoffeeProductDomain

class ICoffeeRepository(ABC):
    @abstractmethod
    def get_cheapest_products(
        self,
        sort_by: Literal["kilo", "unit"] = "kilo",
        limit: int = 10,
        offset: int = 0,
        only_available: bool = True,
        store_name: Optional[str] = None,
        min_weight_g: Optional[int] = None,
        max_weight_g: Optional[int] = None,
        search_query: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        process: Optional[str] = None,
        country: Optional[str] = None,
        variety: Optional[str] = None,
        tasting_notes: Optional[str] = None,
        min_price_kilo: Optional[int] = None,
        max_price_kilo: Optional[int] = None,
        category: Optional[str] = "cafe",
        en_oferta: Optional[bool] = None,
        roast: Optional[str] = None,
        decaf: Optional[bool] = None,
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
        max_price: Optional[int] = None,
        process: Optional[str] = None,
        country: Optional[str] = None,
        variety: Optional[str] = None,
        tasting_notes: Optional[str] = None,
        min_price_kilo: Optional[int] = None,
        max_price_kilo: Optional[int] = None,
        category: Optional[str] = "cafe",
        en_oferta: Optional[bool] = None,
        roast: Optional[str] = None,
        decaf: Optional[bool] = None,
    ) -> int:
        pass

    @abstractmethod
    def find_matching_products(self, product_id: int) -> List[CoffeeProductDomain]:
        pass
