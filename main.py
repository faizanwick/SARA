from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from database import engine, get_db
import models
from routers import products, sales, prediction
from routers.prediction import router as prediction_router
import pandas as pd
import os
import shutil
import numpy as np
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import datetime
import google.generativeai as genai
from fastapi.responses import JSONResponse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Mount static and templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global connection manager for WebSocket
active_connections: Dict[str, WebSocket] = {}

# Initialize Gemini client
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# In-memory storage for conversation history
conversation_history = {}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

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

# Register routers
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(sales.router, prefix="/sales", tags=["sales"])

# Root route - serve homepage
@app.get("/", response_class=HTMLResponse)
async def serve_homepage(request: Request):
    return templates.TemplateResponse("homepage.html", {"request": request})

# Dashboard route (moved from root)
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse("temp.html", {"request": request})

@app.get("/input", response_class=HTMLResponse)
def get_input_form(request: Request):
    return templates.TemplateResponse("input.html", {"request": request})

@app.get("/sales-input", response_class=HTMLResponse)
async def sales_input(request: Request):
    return templates.TemplateResponse("sales_input.html", {"request": request})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["https://your-domain.com"]
    allow_methods=["POST", "GET", "OPTIONS", "CONNECT", "DELETE", "PATCH", "PUT"],
    allow_headers=["*"],
    allow_credentials=True
)

# ✅ Root route: serve index.html frontend
@app.get("/predictor", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse("predict.html", {"request": request})

# Include prediction routes
app.include_router(prediction_router, prefix="/api")

@app.get("/market", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse("market.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    try:
        form_data = await request.form()
        username = form_data.get("username")
        
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")
        
        # Check if user exists, if not create new user
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            user = models.User(username=username)
            db.add(user)
            db.commit()
        
        # Return JSON with success and username
        return JSONResponse(
            content={"success": True, "username": username},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

@app.get("/chat")
async def chat_page(request: Request, db: Session = Depends(get_db)):
    try:
        # Get all users for the chat interface
        users = db.query(models.User).all()
        
        # Get username from query parameter
        username = request.query_params.get("username", "")
        if not username:
            return RedirectResponse(url="/login")
            
        # Verify user exists
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            return RedirectResponse(url="/login")
        
        return templates.TemplateResponse("chat.html", {
            "request": request,
            "username": username,
            "users": users,
            "recent_users": users[:5]  # Show first 5 users as recent
        })
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

@app.get("/marketing-strategies")
def marketing_strategies(request: Request):
    return templates.TemplateResponse("marketing-strategies.html", {"request": request})

@app.get("/profit", response_class=HTMLResponse)
async def profit_analysis(request: Request):
    return templates.TemplateResponse("profit.html", {"request": request})

@app.post("/profit")
async def analyze_profit_data(request: Request, db: Session = Depends(get_db)):
    try:
        # Get all products and their sales
        products = db.query(models.Product).all()
        
        # Prepare data for analysis
        data = []
        for product in products:
            # Get all sales for this product
            sales = db.query(models.Sale).filter(models.Sale.product_id == product.id).all()
            
            # Calculate total units sold
            total_units = sum(sale.quantity for sale in sales)
            
            # For each product, we'll consider:
            # - cost_price: the original price set in /input (product.price)
            # - selling_price: average of actual sale prices from /sales-input
            if total_units > 0:
                # Calculate weighted average of actual selling prices
                total_revenue = sum(sale.price_at_sale * sale.quantity for sale in sales)
                avg_selling_price = total_revenue / total_units
            else:
                # If no sales, use current price as selling price
                avg_selling_price = product.price
            
            data.append({
                'product_id': product.id,
                'category': product.category,
                'cost_price': product.price,  # Original price from /input
                'selling_price': avg_selling_price,  # Average price from actual sales
                'units_sold': total_units
            })
            
            # Log the data for debugging
            print(f"Product {product.name}:")
            print(f"  Original price (cost): ${product.price}")
            print(f"  Avg selling price: ${avg_selling_price}")
            print(f"  Units sold: {total_units}")
            if sales:
                print("  Sale prices:", [f"${sale.price_at_sale} (qty: {sale.quantity})" for sale in sales])
            print("---")
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(data)
        
        roadmap, summary_stats = analyze_profit(df)
        return templates.TemplateResponse(
            "profit.html",
            {
                "request": request,
                "roadmap": roadmap,
                "summary_stats": summary_stats
            }
        )
    
    except Exception as e:
        print(f"Error in profit analysis: {str(e)}")  # Debug log
        return templates.TemplateResponse(
            "profit.html",
            {"request": request, "error": f"Error processing data: {str(e)}"}
        )

@app.websocket("/ws/{sender}/{receiver}")
async def websocket_endpoint(websocket: WebSocket, sender: str, receiver: str, db: Session = Depends(get_db)):
    logger.info(f"WebSocket connection attempt from {sender} to {receiver}")
    try:
        # Accept the connection first
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for {sender}")
        
        # Store the connection
        active_connections[sender] = websocket
        
        # Get or create users
        sender_user = db.query(models.User).filter_by(username=sender).first()
        receiver_user = db.query(models.User).filter_by(username=receiver).first()
        
        logger.info(f"Sender user: {sender_user and sender_user.username}")
        logger.info(f"Receiver user: {receiver_user and receiver_user.username}")
        
        if not sender_user or not receiver_user:
            logger.error(f"User not found - sender: {bool(sender_user)}, receiver: {bool(receiver_user)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        try:
            logger.info(f"Starting message loop for {sender}")
            while True:
                # Wait for messages
                data = await websocket.receive_text()
                logger.info(f"Received message from {sender}: {data}")
                
                # Save message to database
                message = models.Message(
                    sender_id=sender_user.id,
                    receiver_id=receiver_user.id,
                    content=data
                )
                db.add(message)
                db.commit()

                # Format message
                formatted_msg = f"{sender}: {data}"
                
                # Send to receiver if they're connected
                if receiver in active_connections:
                    try:
                        await active_connections[receiver].send_text(formatted_msg)
                        logger.info(f"Message sent to receiver {receiver}")
                    except Exception as e:
                        logger.error(f"Error sending to receiver: {str(e)}")
                        # Remove dead connection
                        del active_connections[receiver]
                else:
                    logger.info(f"Receiver {receiver} not connected")
                
                # Send back to sender for confirmation
                try:
                    await websocket.send_text(formatted_msg)
                    logger.info(f"Message sent back to sender {sender}")
                except Exception as e:
                    logger.error(f"Error sending to sender: {str(e)}")
                    break
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for {sender}")
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            # Clean up connection
            if sender in active_connections:
                del active_connections[sender]
            logger.info(f"Cleaned up connection for {sender}")
            
    except Exception as e:
        logger.error(f"WebSocket setup error: {str(e)}")
        if sender in active_connections:
            del active_connections[sender]
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

@app.post("/negotiate")
async def negotiate(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        product_name = data.get('productName')
        product_price = data.get('productPrice')
        product_quantity = data.get('productQuantity')
        
        # Create a simple negotiation response
        response = f"Negotiation request received for {product_quantity} units of {product_name} at ${product_price} each."
        
        return JSONResponse(content={"response": response})
    except Exception as e:
        return JSONResponse(
            content={"error": f"Negotiation failed: {str(e)}"},
            status_code=500
        )