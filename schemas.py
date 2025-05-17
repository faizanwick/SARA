from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from typing import List, Dict
from pydantic import BaseModel


# Shared product fields
class ProductBase(BaseModel):
    name: str
    price: float
    category: str
    status: str
    total_orders: Optional[int] = 0
    # rating: Optional[float] = 0.0
    image_url: Optional[str] = None

# For creating new product
class ProductCreate(ProductBase):
    pass

# For returning product from DB
class ProductOut(ProductBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class SaleBase(BaseModel):
    product_id: int
    quantity: int
    sale_date: datetime
    price_at_sale: float

class SaleCreate(BaseModel):
    product_id: int
    quantity: int
    price_at_sale: float
    sale_date: date

class SaleOut(SaleBase):
    id: int
    product_id: int
    quantity: int
    price_at_sale: float
    sale_date: datetime
    product: ProductOut

    class Config:
        orm_mode = True

class SaleSummary(BaseModel):
    total_sales: float
    sales_growth: float
    total_orders: int
    orders_growth: float
    total_customers: int
    customer_growth: float
    top_categories: List[str]


# Adnan's code
class PredictionSummary(BaseModel):
    predicted_revenue: float
    predicted_units: int
    prediction_confidence: float

class TrendPoint(BaseModel):
    period: str
    value: int

class SalesTrend(BaseModel):
    labels: List[str]
    data: List[int]

class BestSeller(BaseModel):
    product: str
    total_units: int

class PredictionResponse(BaseModel):
    summary: PredictionSummary
    trend: SalesTrend
    best_sellers: List[BestSeller]
