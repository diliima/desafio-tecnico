import pandas as pd
import os
from pathlib import Path
from .utils import DataNormalizer, load_jsonl, create_output_dirs, generate_report

class DataPipeline:
    """Pipeline principal de ETL"""
    
    def __init__(self, raw_data_path: str = "raw", output_path: str = "data"):
        self.raw_data_path = Path(raw_data_path)
        self.output_path = Path(output_path)
        self.normalizer = DataNormalizer()
        
        # Criar diretórios de saída
        create_output_dirs(self.output_path)
    
    def run_pipeline(self):
        """Executa o pipeline completo"""
        print("🚀 Iniciando pipeline de dados...")
        
        # 1. Processar produtos
        print("📦 Processando produtos...")
        products_df = pd.read_csv(self.raw_data_path / "products.csv")
        clean_products, quarantine_products = self.normalizer.normalize_products(products_df)
        
        # 2. Processar vendors
        print("🏭 Processando vendors...")
        vendors_data = load_jsonl(self.raw_data_path / "vendors.jsonl")
        clean_vendors, quarantine_vendors = self.normalizer.normalize_vendors(vendors_data)
        
        # 3. Processar inventory (se existir)
        print("📊 Processando inventory...")
        inventory_df = self._load_inventory()
        
        # 4. Salvar dados limpos
        self._save_clean_data(clean_products, clean_vendors, inventory_df)
        
        # 5. Salvar quarentena
        self._save_quarantine_data(quarantine_products, quarantine_vendors)
        
        print("✅ Pipeline concluído com sucesso!")
        
        # 6. Relatório
        generate_report(clean_products, clean_vendors, inventory_df, 
                       quarantine_products, quarantine_vendors, self.output_path)
    
    def _load_inventory(self) -> pd.DataFrame:
        """Carrega inventory.parquet se existir"""
        inventory_path = self.raw_data_path / "inventory.parquet"
        if inventory_path.exists():
            return pd.read_parquet(inventory_path)
        else:
            # Criar DataFrame vazio com schema correto
            return pd.DataFrame(columns=['product_id', 'warehouse', 'on_hand', 
                                       'min_stock', 'last_counted_at'])
    
    def _save_clean_data(self, products_df: pd.DataFrame, vendors_df: pd.DataFrame, 
                        inventory_df: pd.DataFrame):
        """Salva dados limpos em formato parquet"""
        
        # Salvar dim_product
        if not products_df.empty:
            products_df.to_parquet(
                self.output_path / "dim_product" / "dim_product.parquet",
                index=False
            )
            print(f"✅ Salvos {len(products_df)} produtos limpos")
        
        # Salvar dim_vendor  
        if not vendors_df.empty:
            vendors_df.to_parquet(
                self.output_path / "dim_vendor" / "dim_vendor.parquet", 
                index=False
            )
            print(f"✅ Salvos {len(vendors_df)} vendors limpos")
        
        # Salvar fact_inventory
        if not inventory_df.empty:
            inventory_df.to_parquet(
                self.output_path / "fact_inventory" / "fact_inventory.parquet",
                index=False
            )
            print(f"✅ Salvos {len(inventory_df)} registros de inventory")
    
    def _save_quarantine_data(self, quarantine_products: pd.DataFrame, 
                             quarantine_vendors: pd.DataFrame):
        """Salva dados em quarentena"""
        
        if not quarantine_products.empty:
            quarantine_products.to_parquet(
                self.output_path / "silver" / "_quarantine" / "products_quarantine.parquet",
                index=False
            )
            print(f"⚠️ {len(quarantine_products)} produtos em quarentena")
        
        if not quarantine_vendors.empty:
            quarantine_vendors.to_parquet(
                self.output_path / "silver" / "_quarantine" / "vendors_quarantine.parquet", 
                index=False
            )
            print(f"⚠️ {len(quarantine_vendors)} vendors em quarentena")

def main():
    """Função principal para execução do pipeline"""
    pipeline = DataPipeline(
        raw_data_path="raw",
        output_path="data"
    )
    
    pipeline.run_pipeline()

if __name__ == "__main__":
    main()