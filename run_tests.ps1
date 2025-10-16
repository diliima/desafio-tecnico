# Script PowerShell para executar testes
# Uso: .\run_tests.ps1 [-Type <all|etl|rag|integration>] [-Coverage] [-Parallel]

param(
    [Parameter(Position=0)]
    [ValidateSet('all', 'etl', 'rag', 'integration', 'smoke', 'e2e')]
    [string]$Type = 'all',
    
    [switch]$Coverage,
    [switch]$Parallel,
    [switch]$Verbose,
    [switch]$Failed
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "🧪 Executando Testes do Sistema" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Verificar se pytest está instalado
try {
    $null = pytest --version 2>&1
} catch {
    Write-Host "❌ pytest não está instalado" -ForegroundColor Red
    Write-Host "Instale com: pip install pytest" -ForegroundColor Yellow
    exit 1
}

# Construir comando
$cmd = "pytest tests/"

# Adicionar verbosidade
if ($Verbose) {
    $cmd += " -v"
} else {
    $cmd += " -v"  # Sempre verboso por padrão
}

# Cores
$cmd += " --color=yes"

# Filtrar por tipo
switch ($Type) {
    'etl' {
        $cmd = "pytest tests/test_etl_validation.py -v"
        Write-Host "📋 Executando apenas testes ETL`n" -ForegroundColor Yellow
    }
    'rag' {
        $cmd = "pytest tests/test_rag_queries.py -v"
        Write-Host "🤖 Executando apenas testes RAG`n" -ForegroundColor Yellow
    }
    'integration' {
        $cmd = "pytest tests/test_integration.py -v"
        Write-Host "🔗 Executando apenas testes de integração`n" -ForegroundColor Yellow
    }
    'smoke' {
        $cmd += " -m smoke"
        Write-Host "💨 Executando apenas smoke tests`n" -ForegroundColor Yellow
    }
    'e2e' {
        $cmd += " -m e2e"
        Write-Host "🎯 Executando testes end-to-end`n" -ForegroundColor Yellow
    }
    default {
        Write-Host "🔄 Executando todos os testes`n" -ForegroundColor Yellow
    }
}

# Adicionar cobertura
if ($Coverage) {
    try {
        $null = pytest --co --cov 2>&1
        $cmd += " --cov=src --cov-report=html --cov-report=term"
        Write-Host "📊 Cobertura de código será gerada`n" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  pytest-cov não instalado. Instale com: pip install pytest-cov" -ForegroundColor Yellow
    }
}

# Adicionar paralelização
if ($Parallel) {
    try {
        $null = pytest --co -n 1 2>&1
        $cmd += " -n auto"
        Write-Host "⚡ Executando testes em paralelo`n" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  pytest-xdist não instalado. Instale com: pip install pytest-xdist" -ForegroundColor Yellow
    }
}

# Executar apenas testes que falharam
if ($Failed) {
    $cmd += " --lf"
    Write-Host "🔄 Executando apenas testes que falharam anteriormente`n" -ForegroundColor Yellow
}

# Executar
Write-Host "Executando: $cmd`n" -ForegroundColor Cyan
Invoke-Expression $cmd

$exitCode = $LASTEXITCODE

# Verificar resultado
if ($exitCode -eq 0) {
    Write-Host "`n✅ Todos os testes passaram!" -ForegroundColor Green
    
    if ($Coverage -and (Test-Path "htmlcov/index.html")) {
        $reportPath = Resolve-Path "htmlcov/index.html"
        Write-Host "`n📊 Relatório de cobertura: $reportPath" -ForegroundColor Cyan
        Write-Host "   Para visualizar, abra o arquivo no navegador" -ForegroundColor Cyan
    }
} else {
    Write-Host "`n❌ Alguns testes falharam (código: $exitCode)" -ForegroundColor Red
}

exit $exitCode
