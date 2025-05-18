from fastapi import APIRouter, HTTPException, Form, Query
from predictor import SalesPredictor
import pandas as pd
from typing import Dict, Any
import logging
from sqlalchemy.orm import Session
from database import get_db
from fastapi import Depends
from models import Product, Sale
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
predictor = SalesPredictor()

@router.get("/predict")
async def predict_sales(
    timeframe: int = Query(default=30, description="Prediction timeframe in days"),
    db: Session = Depends(get_db)
) -> Dict[Any, Any]:
    logger.info(f"Generating prediction for timeframe: {timeframe}")
    
    # Validate timeframe
    if timeframe not in [30, 60, 90]:
        raise HTTPException(
            status_code=400,
            detail="Timeframe must be 30, 60, or 90 days"
        )
    
    try:
        # Get all products and their sales
        products = db.query(Product).all()
        
        # Prepare data for prediction
        data = []
        for product in products:
            # Get sales for this product
            sales = db.query(Sale).filter(Sale.product_id == product.id).all()
            
            # Calculate overall sales
            overall_sales = sum(sale.quantity for sale in sales)
            
            # Get the most recent sale date or use product creation date
            latest_sale = max((sale.sale_date for sale in sales), default=product.created_at)
            
            data.append({
                'product_name': product.name,
                'price': product.price,
                'overall_sales': overall_sales,
                'date': latest_sale.strftime('%Y-%m-%d')
            })
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        logger.debug(f"Generating predictions for {timeframe} days...")
        # Generate predictions with specified timeframe
        try:
            predictions = predictor.predict(df, timeframe)
            logger.debug("Predictions generated successfully")
        except Exception as e:
            logger.error(f"Error in prediction: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(e)}")
        
        response_data = {
            "prediction_summary": {
                "predicted_revenue": predictions["total_revenue"],
                "predicted_units": predictions["total_units"],
                "prediction_confidence": predictions["confidence"]
            },
            "sales_trend": predictions["sales_trend"],
            "best_selling_products": predictions["best_sellers"]
        }
        logger.info(f"Successfully processed {timeframe}-day prediction request")
        return response_data
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 