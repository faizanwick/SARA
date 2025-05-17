from database import engine
import models

def recreate_tables():
    # Drop all tables
    models.Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    models.Base.metadata.create_all(bind=engine)
    
    print("Tables recreated successfully!")

if __name__ == "__main__":
    recreate_tables() 