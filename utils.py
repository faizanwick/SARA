import pandas as pd
import numpy as np
from typing import Tuple, List, Dict
from .schemas import PredictionSummary, SalesTrend, BestSeller

def load_csv(file_bytes) -> pd.DataFrame:
    df = pd.read_csv(file_bytes, parse_dates=['date_sold'])
    return df

def compute_best_sellers(df: pd.DataFrame, top_n: int = 5) -> List[BestSeller]:
    agg = df.groupby('product_name')['units_sold'].sum().reset_index()
    top = agg.sort_values('units_sold', ascending=False).head(top_n)
    return [BestSeller(product=row.product_name, total_units=int(row.units_sold))
            for _, row in top.iterrows()]

def forecast_summary(df: pd.DataFrame, days_ahead: int = 30) -> PredictionSummary:
    # Very simple “forecast”: use last 30 days average × days_ahead
    recent = df[df['date_sold'] >= df.date_sold.max() - pd.Timedelta(days=30)]
    avg_units_per_day = recent['units_sold'].sum() / 30
    predicted_units = int(avg_units_per_day * days_ahead)
    # revenue proportionally
    price_per_unit = (recent['revenue'] / recent['units_sold']).mean()
    predicted_revenue = predicted_units * price_per_unit
    # dummy confidence
    confidence = float(min(0.99, np.random.normal(0.85, 0.05)))
    return PredictionSummary(
        predicted_revenue=round(predicted_revenue, 2),
        predicted_units=predicted_units,
        prediction_confidence=round(confidence * 100, 2)
    )

def build_trend(df: pd.DataFrame) -> SalesTrend:
    # group last 4 weeks
    df = df.set_index('date_sold')
    weekly = df['units_sold'].resample('W').sum().tail(4)
    labels = [f"Week {i+1}" for i in range(len(weekly))]
    return SalesTrend(labels=labels, data=[int(x) for x in weekly.values])
