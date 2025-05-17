from models import Product, Sale
import models
from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
import schemas
import os

print("crud.py loaded, models imported:", Product, Sale)


# def get_top_products(db: Session, limit: int = 5):
#     return db.query(models.Product).order_by(models.Product.total_orders.desc()).limit(limit).all()

def get_products(db: Session):
    return db.query(Product).all()

def get_top_products(db: Session, limit: int = 5):
    try:
        return db.query(Product).order_by(Product.total_orders.desc()).limit(limit).all()
    except Exception as e:
        print("Error in get_top_products:", e)
        return []


def get_recent_orders(db: Session, limit: int = 10):
    return db.query(models.Product).order_by(models.Product.created_at.desc()).limit(limit).all()

def get_category_counts(db: Session):
    return db.query(
        models.Product.category,
        func.count(models.Product.category)
    ).group_by(models.Product.category).all()

def create_sale(db: Session, sale: schemas.SaleCreate):
    # Convert date to datetime with current time
    sale_dict = sale.dict()
    if isinstance(sale_dict['sale_date'], date):
        sale_dict['sale_date'] = datetime.combine(sale_dict['sale_date'], datetime.now().time())
    
    db_sale = models.Sale(**sale_dict)
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
    return db_sale

def get_sales_by_months(db: Session, months: int):
    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=30 * months)
    return db.query(Sale).filter(Sale.sale_date >= cutoff_date).order_by(Sale.sale_date.desc()).all()

def delete_product(db: Session, product_id: int):
    # First delete associated sales
    db.query(models.Sale).filter(models.Sale.product_id == product_id).delete()
    
    # Then delete the product
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        return False
        
    # Delete the product's image if it exists
    if product.image_url and os.path.exists(product.image_url):
        try:
            os.remove(product.image_url)
        except Exception as e:
            print(f"Error deleting image file: {e}")
    
    db.delete(product)
    db.commit()
    return True
