from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from predictor import SalesPredictor
import pandas as pd
from io import StringIO
import json
from typing import Dict, Any
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
predictor = SalesPredictor()

@router.post("/predict")
async def predict_sales(
    file: UploadFile = File(...),
    timeframe: int = Form(default=30)  # Accept timeframe as form data
) -> Dict[Any, Any]:
    logger.info(f"Received file: {file.filename} with timeframe: {timeframe}")
    
    # Validate timeframe
    if timeframe not in [30, 60, 90]:
        raise HTTPException(
            status_code=400,
            detail="Timeframe must be 30, 60, or 90 days"
        )
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        # Read the CSV file
        contents = await file.read()
        logger.debug("File read successfully")
        
        try:
            df = pd.read_csv(StringIO(contents.decode('utf-8')))
            logger.debug(f"CSV parsed successfully. Columns: {df.columns.tolist()}")
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error parsing CSV file: {str(e)}")
        
        # Validate required columns
        required_columns = ['product_name', 'price', 'overall_sales', 'date']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing columns: {missing_columns}")
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        logger.debug(f"Generating predictions for {timeframe} days...")
        # Generate predictions with specified timeframe
        try:
            predictions = predictor.predict(df, timeframe)
            logger.debug("Predictions generated successfully")
        except Exception as e:
            logger.error(f"Error in prediction: {str(e)}\n{traceback.format_exc()}")
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
        logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e)) 