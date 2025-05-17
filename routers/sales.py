from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import crud, schemas
from database import SessionLocal
from datetime import datetime, timedelta
from sqlalchemy import func
from models import Sale, Product
from schemas import SaleSummary


router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create sale (used by sales_input.html)
@router.post("/", response_model=schemas.SaleOut)
def create_sale(sale: schemas.SaleCreate, db: Session = Depends(get_db)):
    return crud.create_sale(db, sale)

# Read sales for last N months (detailed records)
@router.get("/", response_model=List[schemas.SaleOut])
def read_sales(months: int = Query(1, ge=1, le=6), db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=30 * months)
    sales = (
        db.query(Sale)
        .options(joinedload(Sale.product))  # this ensures product is loaded
        .filter(Sale.sale_date >= cutoff)
        .order_by(Sale.sale_date.desc())
        .all()
    )
    return sales

# Recent orders (used in dashboard list)
@router.get("/recent-orders")
def get_recent_orders(db: Session = Depends(get_db)):
    result = (
        db.query(Sale, Product)
        .join(Product, Sale.product_id == Product.id)
        .order_by(Sale.sale_date.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "product_name": product.name,
            "price_at_sale": sale.price_at_sale,
            "quantity": sale.quantity,
            "sale_date": sale.sale_date.isoformat()
        }
        for sale, product in result
    ]

# Sales summary (for dashboard metrics)
@router.get("/summary", response_model=schemas.SaleSummary)
def get_summary(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    last_month = start_of_month - timedelta(days=30)
    
    sales_this_month = db.query(func.sum(Sale.price_at_sale * Sale.quantity)).filter(Sale.sale_date >= start_of_month).scalar() or 0
    sales_last_month = db.query(func.sum(Sale.price_at_sale * Sale.quantity)).filter(Sale.sale_date >= last_month, Sale.sale_date < start_of_month).scalar() or 0
    
    orders_this_month = db.query(func.count(Sale.id)).filter(Sale.sale_date >= start_of_month).scalar() or 0
    orders_last_month = db.query(func.count(Sale.id)).filter(Sale.sale_date >= last_month, Sale.sale_date < start_of_month).scalar() or 0
    
    total_customers = db.query(func.count(func.distinct(Sale.product_id))).scalar() or 0  # Placeholder for customers
    
    top_categories = (
        db.query(Product.category, func.count(Product.category))
        .group_by(Product.category)
        .order_by(func.count(Product.category).desc())
        .limit(3)
        .all()
    )

    def calc_growth(prev, curr):
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return round(((curr - prev) / prev) * 100, 2)

    return {
        "total_sales": round(sales_this_month, 2),
        "sales_growth": calc_growth(sales_last_month, sales_this_month),
        "total_orders": orders_this_month,
        "orders_growth": calc_growth(orders_last_month, orders_this_month),
        "total_customers": total_customers,
        "customer_growth": 0,
        "top_categories": [cat for cat, _ in top_categories]
    }

# Delete all sales records for a product
@router.delete("/product/{product_id}")
def delete_product_sales(product_id: int, db: Session = Depends(get_db)):
    try:
        # Delete all sales records for this product
        db.query(Sale).filter(Sale.product_id == product_id).delete()
        db.commit()
        return {"message": "Sales records deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
