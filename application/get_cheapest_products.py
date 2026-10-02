from typing import List, Literal, Optional
from domain.repositories import ICoffeeRepository
from domain.models import CoffeeProductDomain

class GetCheapestProductsUseCase:
    def __init__(self, repository: ICoffeeRepository):
        self.repository = repository

    def execute(
        self, 
        sort_by: Literal["kilo", "unit"] = "kilo", 
        limit: int = 10, 
        only_available: bool = True,
        store_name: Optional[str] = None,
        min_weight_g: Optional[int] = None,
        max_weight_g: Optional[int] = None,
        search_query: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        process: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[CoffeeProductDomain]:
        
        return self.repository.get_cheapest_products(
            sort_by=sort_by, 
            limit=limit, 
            only_available=only_available,
            store_name=store_name,
            min_weight_g=min_weight_g,
            max_weight_g=max_weight_g,
            search_query=search_query,
            min_price=min_price,
            max_price=max_price
            ,process=process,
            country=country,
        )
