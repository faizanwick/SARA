from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
import os
from typing import List, Dict, Any
import shutil
import numpy as np

app = FastAPI(title="ProfitMAX")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def analyze_profit(data: pd.DataFrame) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    # Clean the data - replace NaN with 0
    data = data.fillna(0)
    
    # Convert numeric columns to appropriate types
    data['cost_price'] = pd.to_numeric(data['cost_price'], errors='coerce').fillna(0)
    data['selling_price'] = pd.to_numeric(data['selling_price'], errors='coerce').fillna(0)
    data['units_sold'] = pd.to_numeric(data['units_sold'], errors='coerce').fillna(0).astype(int)
    
    # Calculate profit metrics
    data['profit_per_unit'] = data['selling_price'] - data['cost_price']
    data['total_profit'] = data['profit_per_unit'] * data['units_sold']
    data['profit_margin'] = (data['profit_per_unit'] / data['selling_price']) * 100
    data['profit_margin'] = data['profit_margin'].replace([np.inf, -np.inf], 0)  # Handle division by zero
    
    roadmap = []
    summary_stats = {
        'total_products': len(data),
        'high_profit': 0,
        'needs_review': 0,
        'clear_stock': 0,
        'total_profit': float(data['total_profit'].sum()),
        'avg_margin': float(data['profit_margin'].mean()),
        'top_products': [],
        'worst_products': []
    }

    for _, row in data.iterrows():
        if row['profit_per_unit'] >= 50 and row['units_sold'] >= 100:
            strategy = "Maintain current strategy - this product is performing well"
            strategy_type = "keep"
            summary_stats['high_profit'] += 1
        elif row['profit_per_unit'] < 20 and row['units_sold'] >= 100:
            strategy = "Increase price by 5-10% or bundle with complementary products"
            strategy_type = "increase"
            summary_stats['needs_review'] += 1
        elif row['profit_per_unit'] >= 50 and row['units_sold'] < 20:
            strategy = "Boost marketing efforts and improve product visibility"
            strategy_type = "promote"
            summary_stats['needs_review'] += 1
        else:
            strategy = "Run clearance sale or consider discontinuing the product"
            strategy_type = "clear"
            summary_stats['clear_stock'] += 1

        roadmap.append({
            "product_id": str(row['product_id']),
            "category": str(row['category']),
            "strategy": strategy,
            "type": strategy_type,
            "profit_per_unit": f"${row['profit_per_unit']:.2f}",
            "units_sold": int(row['units_sold']),
            "total_profit": f"${row['total_profit']:.2f}",
            "profit_margin": f"{row['profit_margin']:.1f}%"
        })
    
    # Get top and worst products
    summary_stats['top_products'] = data.nlargest(5, 'total_profit')[['product_id', 'category', 'total_profit']].to_dict('records')
    summary_stats['worst_products'] = data.nsmallest(5, 'total_profit')[['product_id', 'category', 'total_profit']].to_dict('records')
    
    return roadmap, summary_stats

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/")
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": "Please upload a valid CSV file"}
        )
    
    try:
        # Save uploaded file
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the file
        df = pd.read_csv(file_path)
        required_columns = ['product_id', 'category', 'cost_price', 'selling_price', 'units_sold']
        
        if not all(col in df.columns for col in required_columns):
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "error": f"Missing required columns. Your file needs: {', '.join(required_columns)}"
                }
            )
        
        roadmap, summary_stats = analyze_profit(df)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "roadmap": roadmap,
                "summary_stats": summary_stats
            }
        )
    
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": f"Error processing file: {str(e)}"}
        )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)