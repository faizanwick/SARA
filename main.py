from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from database import engine
import models
from routers import products, sales, prediction
from fastapi.middleware.cors import CORSMiddleware
from routers.prediction import router as prediction_router


app = FastAPI()

models.Base.metadata.create_all(bind=engine)

# Mount static and templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routers
# app.include_router(products.router, prefix="/products")
app.include_router(products.router, prefix="/products", tags=["Products"])
# app.include_router(sales.router, prefix="/sales")
app.include_router(sales.router, prefix="/sales", tags=["sales"])

# Serve index.html from templates
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
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
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ✅ Root route: serve index.html frontend
@app.get("/predictor", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse("predict.html", {"request": request})

# Include prediction routes
app.include_router(prediction_router, prefix="/api")