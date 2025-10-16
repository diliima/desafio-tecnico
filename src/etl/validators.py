from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import date
import re

# Esquemas para dados brutos
class RawProduct(BaseModel):
    product_id: Optional[int]
    sku: str
    model: Optional[str]
    category: str
    weight_grams: Optional[float]
    dimensions_mm: Optional[str]
    vendor_code: str
    launch_date: str
    msrp_usd: str
    
    @validator('msrp_usd')
    def normalize_price(cls, v):
        # Normalizar vírgula para ponto
        return v.replace(',', '.') if isinstance(v, str) else v

class RawVendor(BaseModel):
    vendor_code: str
    name: str
    country: str
    support_email: EmailStr

# Esquemas para dados limpos (dimensionais)
class DimProduct(BaseModel):
    product_id: int
    sku: str
    model: Optional[str]
    category: str
    weight_g: Optional[int]
    length_mm: Optional[int]
    width_mm: Optional[int]
    height_mm: Optional[int]
    vendor_code: str
    launch_date: Optional[date]
    msrp_usd: Optional[float]
    
    @validator('weight_g')
    def validate_weight(cls, v):
        if v is not None and v <= 0:
            raise ValueError('weight_g must be positive')
        return v
    
    @validator('msrp_usd')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('msrp_usd must be non-negative')
        return v

class DimVendor(BaseModel):
    vendor_code: str
    vendor_name: str
    country: str
    support_email: EmailStr

class FactInventory(BaseModel):
    product_id: int
    warehouse: str
    on_hand: int
    min_stock: int
    last_counted_at: date

# Funções de validação auxiliares
def is_valid_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, str(email)) is not None

def validate_product_row(row: dict) -> list:
    """Valida uma linha de produto normalizada"""
    errors = []
    
    if not row.get('sku'):
        errors.append("SKU is required")
    
    if row.get('weight_g') is not None and row['weight_g'] <= 0:
        errors.append("weight_g must be positive")
    
    if row.get('msrp_usd') is not None and row['msrp_usd'] < 0:
        errors.append("msrp_usd must be non-negative")
    
    # Validar se dimensões estão completas
    dims = [row.get('length_mm'), row.get('width_mm'), row.get('height_mm')]
    if any(d is not None for d in dims) and any(d is None for d in dims):
        errors.append("dimensions_mm must be complete (length x width x height)")
    
    return errors