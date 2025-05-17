from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import crud, schemas
from database import SessionLocal
from models import Product
from sqlalchemy import func
import shutil
import os

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create a new product with quantity and image upload
@router.post("/", response_model=schemas.ProductOut)
def create_product(
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    quantity: str = Form(...),  # <-- changed from 'status' to 'quantity'
    total_orders: int = Form(0),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    image_url = None
    if image:
        os.makedirs("static/uploads", exist_ok=True)
        image_path = f"static/uploads/{image.filename}"
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = image_path

    new_product = Product(
        name=name,
        price=price,
        category=category,
        status=quantity,  # <-- Store quantity in the 'status' column
        total_orders=total_orders,
        image_url=image_url
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

# Get all products
@router.get("/", response_model=List[schemas.ProductOut])
def read_products(db: Session = Depends(get_db)):
    return crud.get_products(db)

# Get top products by total_orders (limit 5)
@router.get("/top", response_model=List[schemas.ProductOut])
def read_top_products(db: Session = Depends(get_db)):
    return crud.get_top_products(db, limit=5)

# Get recent orders (limit 10)
@router.get("/recent", response_model=List[schemas.ProductOut])
def read_recent_orders(db: Session = Depends(get_db)):
    return crud.get_recent_orders(db, limit=10)

# Get aggregated product categories count
@router.get("/categories")
def read_categories(db: Session = Depends(get_db)):
    result = db.query(
        Product.category,
        func.count(Product.category)
    ).group_by(Product.category).all()
    return [{"category": category, "count": count} for category, count in result]

# Delete a product by ID
@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    success = crud.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}
