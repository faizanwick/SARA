import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SalesPredictor:
    def __init__(self):
        try:
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            logger.debug("SalesPredictor initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing SalesPredictor: {str(e)}")
            raise
        
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare the data for prediction"""
        try:
            logger.debug("Starting data preparation")
            # Convert date to datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Create time-based features
            df['year'] = df['date'].dt.year
            df['month'] = df['date'].dt.month
            df['day'] = df['date'].dt.day
            df['day_of_week'] = df['date'].dt.dayofweek
            
            logger.debug("Data preparation completed successfully")
            return df
        except Exception as e:
            logger.error(f"Error in data preparation: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Error preparing data: {str(e)}")
        
    def _calculate_confidence(self, predictions, test_predictions) -> float:
        """Calculate prediction confidence based on model performance"""
        try:
            mse = np.mean((test_predictions - predictions[:len(test_predictions)])**2)
            confidence = max(0, min(100, 100 * (1 - np.sqrt(mse) / np.mean(predictions))))
            return round(confidence, 2)
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            raise Exception(f"Error calculating confidence: {str(e)}")
    
    def predict(self, df: pd.DataFrame, timeframe: int = 30) -> dict:
        """Generate predictions for the specified timeframe"""
        try:
            logger.info(f"Starting prediction for timeframe: {timeframe} days")
            
            # Prepare data
            df = self._prepare_data(df)
            logger.debug("Data preparation completed")
            
            # Prepare features for training
            features = ['year', 'month', 'day', 'day_of_week', 'price']
            X = df[features]
            y = df['overall_sales']
            
            logger.debug(f"Training data shape: X={X.shape}, y={y.shape}")
            
            # Split data for training and validation
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model
            self.model.fit(X_train, y_train)
            logger.debug("Model training completed")
            
            # Generate future dates
            last_date = df['date'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), 
                                       periods=timeframe, freq='D')
            
            # Create future features
            future_data = pd.DataFrame({
                'date': future_dates,
                'year': future_dates.year,
                'month': future_dates.month,
                'day': future_dates.day,
                'day_of_week': future_dates.dayofweek,
                'price': df['price'].mean()
            })
            
            logger.debug("Future data prepared")
            
            # Make predictions
            predictions = self.model.predict(future_data[features])
            test_predictions = self.model.predict(X_test)
            
            # Calculate confidence
            confidence = self._calculate_confidence(predictions, y_test)
            logger.debug(f"Prediction confidence: {confidence}%")
            
            # Prepare sales trend data
            sales_trend = []
            for i in range(len(future_dates)):
                sales_trend.append({
                    'date': future_dates[i].strftime('%Y-%m-%d'),
                    'predicted_units': int(predictions[i])
                })
            
            # Calculate total predictions
            total_units = int(sum(predictions))
            total_revenue = float(total_units * df['price'].mean())
            
            # Get best-selling products prediction
            products = df['product_name'].unique()
            best_sellers = []
            
            for product in products:
                product_data = df[df['product_name'] == product]
                product_predictions = self.model.predict(product_data[features])
                
                best_sellers.append({
                    'product_name': product,
                    'category': 'General',  # You might want to add category in your CSV
                    'predicted_units': int(np.mean(product_predictions)),
                    'predicted_revenue': float(np.mean(product_predictions) * product_data['price'].mean()),
                    'confidence': confidence
                })
            
            # Sort best sellers by predicted revenue
            best_sellers.sort(key=lambda x: x['predicted_revenue'], reverse=True)
            best_sellers = best_sellers[:6]  # Keep top 6 as shown in frontend
            
            logger.info("Prediction completed successfully")
            return {
                'total_units': total_units,
                'total_revenue': total_revenue,
                'confidence': confidence,
                'sales_trend': sales_trend,
                'best_sellers': best_sellers
            }
            
        except Exception as e:
            logger.error(f"Error in prediction: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Failed to generate predictions: {str(e)}") 