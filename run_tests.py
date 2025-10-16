#!/usr/bin/env python3
"""
Script de execução de testes com opções de configuração.

Uso:
    python run_tests.py              # Todos os testes
    python run_tests.py --etl        # Apenas testes ETL
    python run_tests.py --rag        # Apenas testes RAG
    python run_tests.py --smoke      # Apenas smoke tests
    python run_tests.py --coverage   # Com cobertura de código
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Executa um comando e exibe o resultado."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode != 0:
        print(f"\n❌ {description} falhou com código {result.returncode}")
        return False
    else:
        print(f"\n✅ {description} concluído com sucesso")
        return True


def main():
    parser = argparse.ArgumentParser(description="Executar testes do sistema")
    
    parser.add_argument('--etl', action='store_true', help='Executar apenas testes ETL')
    parser.add_argument('--rag', action='store_true', help='Executar apenas testes RAG')
    parser.add_argument('--integration', action='store_true', help='Executar apenas testes de integração')
    parser.add_argument('--smoke', action='store_true', help='Executar apenas smoke tests')
    parser.add_argument('--e2e', action='store_true', help='Executar testes end-to-end')
    parser.add_argument('--coverage', action='store_true', help='Gerar relatório de cobertura')
    parser.add_argument('--verbose', '-v', action='store_true', help='Modo verboso')
    parser.add_argument('--parallel', '-n', action='store_true', help='Executar testes em paralelo')
    parser.add_argument('--failed', action='store_true', help='Executar apenas testes que falharam anteriormente')
    
    args = parser.parse_args()
    
    # Verificar se pytest está instalado
    try:
        subprocess.run(['pytest', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pytest não está instalado. Instale com: pip install pytest")
        return 1
    
    # Construir comando base
    cmd_parts = ['pytest', 'tests/']
    
    # Adicionar opções de verbosidade
    if args.verbose:
        cmd_parts.append('-v')
    else:
        cmd_parts.append('-v')  # Sempre verboso por padrão
    
    # Adicionar cores
    cmd_parts.append('--color=yes')
    
    # Filtrar por tipo de teste
    if args.etl:
        cmd_parts.append('tests/test_etl_validation.py')
    elif args.rag:
        cmd_parts.append('tests/test_rag_queries.py')
    elif args.integration:
        cmd_parts.append('tests/test_integration.py')
    elif args.smoke:
        cmd_parts.extend(['-m', 'smoke'])
    elif args.e2e:
        cmd_parts.extend(['-m', 'e2e'])
    
    # Adicionar cobertura
    if args.coverage:
        try:
            subprocess.run(['pytest', '--co', '--cov'], capture_output=True, check=True)
            cmd_parts.extend(['--cov=src', '--cov-report=html', '--cov-report=term'])
        except subprocess.CalledProcessError:
            print("⚠️  pytest-cov não está instalado. Instale com: pip install pytest-cov")
            print("Continuando sem cobertura...\n")
    
    # Adicionar execução paralela
    if args.parallel:
        try:
            subprocess.run(['pytest', '--co', '-n'], capture_output=True, check=True)
            cmd_parts.extend(['-n', 'auto'])
        except subprocess.CalledProcessError:
            print("⚠️  pytest-xdist não está instalado. Instale com: pip install pytest-xdist")
            print("Continuando sem paralelização...\n")
    
    # Executar apenas testes que falharam
    if args.failed:
        cmd_parts.append('--lf')
    
    # Executar testes
    cmd = ' '.join(cmd_parts)
    success = run_command(cmd, "Executando testes")
    
    # Se cobertura foi gerada, mostrar localização do relatório
    if args.coverage and success:
        html_report = Path('htmlcov/index.html')
        if html_report.exists():
            print(f"\n📊 Relatório de cobertura gerado em: {html_report.absolute()}")
            print(f"   Abra no navegador: file:///{html_report.absolute()}")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
