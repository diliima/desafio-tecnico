import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema, Check
import hashlib
import re
import json
from datetime import datetime
from typing import Tuple, Dict, Any
from pathlib import Path
from .validators import is_valid_email, validate_product_row

# Schemas Pandera para validação declarativa
PRODUCT_SCHEMA = DataFrameSchema({
    "product_id": Column(int, Check.greater_than(0), nullable=False),
    "sku": Column(str, Check.str_matches(r'^[A-Z]{2}-\d{3}$'), nullable=False),
    "model": Column(str, nullable=True),
    "category": Column(str, Check.isin(["Router", "Switch", "Camera"]), nullable=False),
    "weight_g": Column(int, Check.greater_than(0), nullable=True),
    "length_mm": Column(int, Check.greater_than(0), nullable=True),
    "width_mm": Column(int, Check.greater_than(0), nullable=True),
    "height_mm": Column(int, Check.greater_than(0), nullable=True),
    "vendor_code": Column(str, Check.str_matches(r'^V-\d{2}$'), nullable=False),
    "launch_date": Column(str, nullable=True),
    "msrp_usd": Column(float, Check.greater_than_or_equal_to(0), nullable=True)
})

VENDOR_SCHEMA = DataFrameSchema({
    "vendor_code": Column(str, Check.str_matches(r'^V-\d{2}$'), nullable=False, unique=True),
    "vendor_name": Column(str, Check.str_length(min_value=2), nullable=False),
    "country": Column(str, Check.str_length(min_value=2, max_value=2), nullable=False),
    "support_email": Column(str, nullable=False)
})

class DataNormalizer:
    """Classe responsável pela normalização dos dados"""
    
    def __init__(self):
        self.validation_errors = []
    
    def normalize_products(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Normaliza dados de produtos e retorna dados limpos + quarentena"""
        clean_data = []
        quarantine_data = []
        
        for idx, row in df.iterrows():
            try:
                normalized_row = self._normalize_product_row(row)
                
                # Validação com Pandera
                try:
                    single_row_df = pd.DataFrame([normalized_row])
                    # Validar apenas as colunas que existem
                    available_cols = [col for col in PRODUCT_SCHEMA.columns.keys() 
                                    if col in single_row_df.columns]
                    
                    if available_cols:
                        subset_schema = DataFrameSchema({
                            col: PRODUCT_SCHEMA.columns[col] for col in available_cols
                        })
                        subset_schema.validate(single_row_df)
                    
                    clean_data.append(normalized_row)
                    
                except pa.errors.SchemaError as e:
                    quarantine_data.append({
                        **row.to_dict(),
                        'validation_errors': str(e),
                        'quarantine_reason': f'Schema validation failed: {str(e)}'
                    })
                    
            except Exception as e:
                quarantine_data.append({
                    **row.to_dict(),
                    'processing_error': str(e),
                    'quarantine_reason': f'Processing error: {str(e)}'
                })
        
        return pd.DataFrame(clean_data), pd.DataFrame(quarantine_data)
    
    def _normalize_product_row(self, row: pd.Series) -> Dict[str, Any]:
        """Normaliza uma linha de produto"""
        normalized = {}
        
        # Gerar product_id se ausente
        if pd.isna(row.get('product_id')) or row.get('product_id') == '':
            sku = str(row.get('sku', ''))
            normalized['product_id'] = self._generate_deterministic_id(sku)
        else:
            normalized['product_id'] = int(row['product_id'])
        
        # Normalizar campos básicos
        normalized['sku'] = str(row.get('sku', '')).strip()
        normalized['model'] = str(row.get('model', '')).strip() if pd.notna(row.get('model')) else None
        normalized['category'] = str(row.get('category', '')).strip()
        normalized['vendor_code'] = str(row.get('vendor_code', '')).strip()
        
        # Normalizar peso
        weight_grams = row.get('weight_grams')
        if pd.notna(weight_grams) and str(weight_grams).strip():
            try:
                normalized['weight_g'] = int(float(str(weight_grams).strip()))
            except:
                normalized['weight_g'] = None
        else:
            normalized['weight_g'] = None
        
        # Normalizar preço (vírgula para ponto)
        msrp = row.get('msrp_usd')
        if pd.notna(msrp) and str(msrp).strip():
            try:
                price_str = str(msrp).replace(',', '.').strip()
                normalized['msrp_usd'] = float(price_str)
            except:
                normalized['msrp_usd'] = None
        else:
            normalized['msrp_usd'] = None
        
        # Normalizar dimensões
        dimensions = self._parse_dimensions(row.get('dimensions_mm', ''))
        normalized.update(dimensions)
        
        # Normalizar data
        normalized['launch_date'] = self._normalize_date(row.get('launch_date'))
        
        return normalized
    
    def _generate_deterministic_id(self, sku: str) -> int:
        """Gera ID determinístico baseado no SKU"""
        hash_object = hashlib.md5(sku.encode())
        return int(hash_object.hexdigest()[:8], 16)
    
    def _parse_dimensions(self, dimensions_str: str) -> Dict[str, int]:
        """Parse dimensions_mm para length, width, height"""
        result = {'length_mm': None, 'width_mm': None, 'height_mm': None}
        
        if not dimensions_str or pd.isna(dimensions_str):
            return result
        
        # Remove espaços e aspas
        clean_str = str(dimensions_str).strip('"').strip()
        
        # Regex para capturar dimensões no formato "220x120x45"
        pattern = r'(\d+)x(\d+)x(\d+)'
        match = re.search(pattern, clean_str)
        
        if match:
            result['length_mm'] = int(match.group(1))
            result['width_mm'] = int(match.group(2))
            result['height_mm'] = int(match.group(3))
        
        return result
    
    def _normalize_date(self, date_str: str) -> str:
        """Normaliza datas inválidas"""
        if not date_str or pd.isna(date_str):
            return None
        
        try:
            # Tentar formato YYYY-MM-DD
            datetime.strptime(str(date_str), '%Y-%m-%d')
            return str(date_str)
        except:
            try:
                # Tentar formato YYYY/MM/DD e corrigir
                parts = str(date_str).split('/')
                if len(parts) == 3:
                    year, month, day = parts
                    # Corrigir meses inválidos (ex: 13 -> 12)
                    month = min(int(month), 12)
                    # Corrigir dias inválidos para fevereiro
                    if int(month) == 2:
                        day = min(int(day), 28)
                    else:
                        day = min(int(day), 30)
                    return f"{year}-{month:02d}-{day:02d}"
            except:
                pass
        
        return None
    
    def normalize_vendors(self, vendors_data: list) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Normaliza dados de vendors, resolvendo duplicatas"""
        # Converter para DataFrame
        df = pd.DataFrame(vendors_data)
        
        # Resolver duplicatas por vendor_code
        clean_vendors = []
        quarantine_vendors = []
        
        for vendor_code, group in df.groupby('vendor_code'):
            try:
                if len(group) > 1:
                    # Política: preferir nome mais recente (último na lista)
                    consolidated = self._consolidate_vendor(group)
                else:
                    vendor = group.iloc[0].to_dict()
                    consolidated = {
                        'vendor_code': vendor['vendor_code'],
                        'vendor_name': vendor['name'],
                        'country': vendor['country'],
                        'support_email': vendor['support_email']
                    }
                
                # Validar com Pandera
                vendor_df = pd.DataFrame([consolidated])
                try:
                    VENDOR_SCHEMA.validate(vendor_df)
                    clean_vendors.append(consolidated)
                except pa.errors.SchemaError as e:
                    quarantine_vendors.append({
                        **consolidated,
                        'validation_errors': str(e),
                        'quarantine_reason': f'Vendor validation failed: {str(e)}'
                    })
                    
            except Exception as e:
                # Em caso de erro, quarentenar todos os registros do grupo
                for _, vendor_row in group.iterrows():
                    quarantine_vendors.append({
                        **vendor_row.to_dict(),
                        'processing_error': str(e),
                        'quarantine_reason': f'Vendor processing error: {str(e)}'
                    })
        
        return pd.DataFrame(clean_vendors), pd.DataFrame(quarantine_vendors)
    
    def _consolidate_vendor(self, vendor_group: pd.DataFrame) -> Dict[str, Any]:
        """Consolida vendors duplicados"""
        # Ordenar por nome (assumindo que mais recente tem nome mais completo)
        sorted_vendors = vendor_group.sort_values('name', key=lambda x: x.str.len(), ascending=False)
        
        primary = sorted_vendors.iloc[0]
        
        return {
            'vendor_code': primary['vendor_code'],
            'vendor_name': primary['name'],
            'country': primary['country'],
            'support_email': primary['support_email']
        }

def load_jsonl(file_path: Path) -> list:
    """Carrega arquivo JSONL"""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data.append(json.loads(line.strip()))
                except json.JSONDecodeError as e:
                    print(f"⚠️ Erro na linha {line_num} do arquivo {file_path}: {e}")
    except FileNotFoundError:
        print(f"⚠️ Arquivo não encontrado: {file_path}")
    return data

def create_output_dirs(output_path: Path):
    """Cria estrutura de diretórios"""
    dirs = [
        output_path / "dim_product",
        output_path / "dim_vendor", 
        output_path / "fact_inventory",
        output_path / "silver" / "_quarantine",
        output_path / "schemas"
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)

def save_data_contracts(output_path: Path):
    """Salva contratos de dados (schemas + regras)"""
    contracts = {
        "version": "1.0.0",
        "schemas": {
            "dim_product": {
                "description": "Tabela dimensional de produtos",
                "columns": {
                    "product_id": {"type": "int", "nullable": False, "primary_key": True},
                    "sku": {"type": "string", "nullable": False, "pattern": "^[A-Z]{2}-\\d{3}$"},
                    "model": {"type": "string", "nullable": True},
                    "category": {"type": "string", "nullable": False, "enum": ["Router", "Switch", "Camera"]},
                    "weight_g": {"type": "int", "nullable": True, "min_value": 1},
                    "length_mm": {"type": "int", "nullable": True, "min_value": 1},
                    "width_mm": {"type": "int", "nullable": True, "min_value": 1},
                    "height_mm": {"type": "int", "nullable": True, "min_value": 1},
                    "vendor_code": {"type": "string", "nullable": False, "pattern": "^V-\\d{2}$"},
                    "launch_date": {"type": "string", "nullable": True, "format": "date"},
                    "msrp_usd": {"type": "float", "nullable": True, "min_value": 0}
                }
            },
            "dim_vendor": {
                "description": "Tabela dimensional de fornecedores",
                "columns": {
                    "vendor_code": {"type": "string", "nullable": False, "primary_key": True},
                    "vendor_name": {"type": "string", "nullable": False, "min_length": 2},
                    "country": {"type": "string", "nullable": False, "length": 2},
                    "support_email": {"type": "string", "nullable": False, "format": "email"}
                }
            }
        },
        "data_quality_rules": {
            "product_completeness": "SKU, category, vendor_code são obrigatórios",
            "vendor_uniqueness": "vendor_code deve ser único",
            "referential_integrity": "vendor_code em products deve existir em vendors",
            "date_policy": "Datas inválidas são corrigidas: mês > 12 → 12, dia > 28 (fev) → 28"
        }
    }
    
    with open(output_path / "schemas" / "data_contracts.json", 'w') as f:
        json.dump(contracts, f, indent=2)

def generate_report(clean_products, clean_vendors, inventory,
                   quarantine_products, quarantine_vendors, output_path: Path):
    """Gera relatório do pipeline"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_summary": {
            "products_processed": len(clean_products) + len(quarantine_products),
            "products_clean": len(clean_products),
            "products_quarantined": len(quarantine_products),
            "vendors_processed": len(clean_vendors) + len(quarantine_vendors),
            "vendors_clean": len(clean_vendors), 
            "vendors_quarantined": len(quarantine_vendors),
            "inventory_records": len(inventory)
        },
        "data_quality_metrics": {
            "product_completeness": len(clean_products) / (len(clean_products) + len(quarantine_products)) if (len(clean_products) + len(quarantine_products)) > 0 else 0,
            "vendor_completeness": len(clean_vendors) / (len(clean_vendors) + len(quarantine_vendors)) if (len(clean_vendors) + len(quarantine_vendors)) > 0 else 0
        }
    }
    
    with open(output_path / "pipeline_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📋 Relatório: {report['pipeline_summary']}")
    return report