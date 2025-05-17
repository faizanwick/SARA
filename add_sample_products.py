from database import SessionLocal, engine
from models import Product
import models

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

def add_sample_products():
    db = SessionLocal()
    try:
        # Check if we already have products
        existing_products = db.query(Product).count()
        if existing_products > 0:
            print("Products already exist in the database.")
            return

        # Sample products
        products = [
            {
                "name": "Laptop",
                "price": 999.99,
                "category": "Electronics",
                "status": "In Stock",
                "total_orders": 0,
                "image_url": "static/uploads/laptop.jpg"
            },
            {
                "name": "Smartphone",
                "price": 699.99,
                "category": "Electronics",
                "status": "In Stock",
                "total_orders": 0,
                "image_url": "static/uploads/phone.jpg"
            },
            {
                "name": "Headphones",
                "price": 199.99,
                "category": "Electronics",
                "status": "In Stock",
                "total_orders": 0,
                "image_url": "static/uploads/headphones.jpg"
            }
        ]

        # Add products to database
        for product_data in products:
            product = Product(**product_data)
            db.add(product)
        
        db.commit()
        print("Sample products added successfully!")

    except Exception as e:
        print(f"Error adding sample products: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_sample_products() 