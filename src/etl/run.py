import pandas as pd
import os
from pathlib import Path
from .utils import DataNormalizer, load_jsonl, create_output_dirs, generate_report, save_data_contracts, save_partitioned_data

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
        try:
            # Tentar ler CSV com diferentes configurações
            products_df = self._load_products_csv()
            clean_products, quarantine_products = self.normalizer.normalize_products(products_df)
        except Exception as e:
            print(f"❌ Erro ao processar produtos: {e}")
            clean_products = pd.DataFrame()
            quarantine_products = pd.DataFrame([{
                'error': str(e),
                'quarantine_reason': f'CSV parsing error: {str(e)}'
            }])
        
        # 2. Processar vendors
        print("🏭 Processando vendors...")
        try:
            vendors_data = load_jsonl(self.raw_data_path / "vendors.jsonl")
            clean_vendors, quarantine_vendors = self.normalizer.normalize_vendors(vendors_data)
        except Exception as e:
            print(f"❌ Erro ao processar vendors: {e}")
            clean_vendors = pd.DataFrame()
            quarantine_vendors = pd.DataFrame([{
                'error': str(e),
                'quarantine_reason': f'Vendor processing error: {str(e)}'
            }])
        
        # 3. Processar inventory (se existir)
        print("📊 Processando inventory...")
        try:
            inventory_df = self._load_inventory()
        except Exception as e:
            print(f"❌ Erro ao processar inventory: {e}")
            inventory_df = pd.DataFrame()
        
        # 4. Salvar dados limpos
        self._save_clean_data(clean_products, clean_vendors, inventory_df)
        
        # 5. Salvar quarentena
        self._save_quarantine_data(quarantine_products, quarantine_vendors)
        
        # 6. Salvar contratos de dados
        save_data_contracts(self.output_path)
        
        print("✅ Pipeline concluído com sucesso!")
        
        # 7. Relatório
        generate_report(clean_products, clean_vendors, inventory_df, 
                       quarantine_products, quarantine_vendors, self.output_path)
    
    def _load_products_csv(self) -> pd.DataFrame:
        """Carrega CSV de produtos com tratamento de erros"""
        csv_path = self.raw_data_path / "products.csv"
        
        # Tentar diferentes estratégias de parsing
        try:
            # Primeira tentativa: parsing normal
            return pd.read_csv(csv_path)
        except pd.errors.ParserError:
            print("⚠️ Erro de parsing CSV, tentando com configurações alternativas...")
            
            try:
                # Segunda tentativa: com quoting flexível
                return pd.read_csv(csv_path, quoting=1, skipinitialspace=True)
            except:
                try:
                    # Terceira tentativa: especificar separador e tratar aspas
                    return pd.read_csv(csv_path, sep=',', quotechar='"', escapechar='\\')
                except:
                    # Última tentativa: ler linha por linha e limpar
                    return self._manual_csv_parse(csv_path)
    
    def _manual_csv_parse(self, csv_path: Path) -> pd.DataFrame:
        """Parse manual do CSV problemático"""
        print("📝 Fazendo parse manual do CSV...")
        
        data = []
        headers = None
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Limpar linha
                clean_line = line.strip()
                
                if line_num == 1:
                    # Header
                    headers = [col.strip() for col in clean_line.split(',')]
                    continue
                
                # Parse da linha de dados
                try:
                    # Dividir por vírgula, mas cuidar com vírgulas dentro de aspas
                    fields = self._split_csv_line(clean_line)
                    
                    # Ajustar número de campos se necessário
                    while len(fields) < len(headers):
                        fields.append('')
                    while len(fields) > len(headers):
                        fields.pop()
                    
                    # Criar dicionário
                    row_dict = dict(zip(headers, fields))
                    data.append(row_dict)
                    
                except Exception as e:
                    print(f"⚠️ Erro na linha {line_num}: {e}")
                    continue
        
        return pd.DataFrame(data)
    
    def _split_csv_line(self, line: str) -> list:
        """Divide linha CSV respeitando aspas"""
        fields = []
        current_field = ""
        in_quotes = False
        
        i = 0
        while i < len(line):
            char = line[i]
            
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                fields.append(current_field.strip().strip('"'))
                current_field = ""
            else:
                current_field += char
            
            i += 1
        
        # Adicionar último campo
        fields.append(current_field.strip().strip('"'))
        
        return fields
    
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
        """Salva dados limpos em formato parquet particionado"""
        
        # Salvar dim_product (particionado por categoria)
        if not products_df.empty:
            save_partitioned_data(
                products_df, 
                self.output_path, 
                "dim_product", 
                partition_cols=['category']
            )
            print(f"✅ Salvos {len(products_df)} produtos limpos (particionado por categoria)")
        
        # Salvar dim_vendor (arquivo único - poucos registros)
        if not vendors_df.empty:
            save_partitioned_data(
                vendors_df,
                self.output_path,
                "dim_vendor"
            )
            print(f"✅ Salvos {len(vendors_df)} vendors limpos")
        
        # Salvar fact_inventory (particionado por warehouse)
        if not inventory_df.empty:
            save_partitioned_data(
                inventory_df,
                self.output_path,
                "fact_inventory",
                partition_cols=['warehouse']
            )
            print(f"✅ Salvos {len(inventory_df)} registros de inventory (particionado por warehouse)")

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
    # Desabilitar warning do Pandera
    os.environ['DISABLE_PANDERA_IMPORT_WARNING'] = 'True'
    
    pipeline = DataPipeline(
        raw_data_path="raw",
        output_path="data"
    )
    
    pipeline.run_pipeline()

if __name__ == "__main__":
    main()