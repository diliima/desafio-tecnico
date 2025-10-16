"""Verifica se a API está acessível."""
import socket
import requests
import subprocess
import sys

def check_port(port=8001):
    """Verifica se algo está na porta."""
    print(f"🔌 Verificando porta {port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result == 0:
        print(f"  ✅ Porta {port} está aberta")
        return True
    else:
        print(f"  ❌ Porta {port} está fechada")
        return False

def check_url(url):
    """Testa uma URL."""
    print(f"\n🌐 Testando {url}...")
    try:
        response = requests.get(url, timeout=3)
        print(f"  Status: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  JSON: {data}")
                return True
            except:
                print(f"  HTML: {response.text[:200]}")
        return False
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return False

def check_processes():
    """Lista processos Python."""
    print("\n🐍 Processos Python rodando:")
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-Process python | Select-Object Id,Path"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except Exception as e:
        print(f"  Erro: {e}")

if __name__ == "__main__":
    print("="*60)
    print("🔍 DIAGNÓSTICO DA API")
    print("="*60)
    
    # Verificar porta
    if not check_port(8000):
        print("\n❌ Nada rodando na porta 8000")
        print("\nInicie a API com:")
        print("  python -m src.rag.api")
        sys.exit(1)
    
    # Testar URLs
    urls = [
        "http://localhost:8001/",
        "http://127.0.0.1:8001/",
        "http://localhost:8001/health"
    ]
    
    working = []
    for url in urls:
        if check_url(url):
            working.append(url)
    
    # Verificar processos
    check_processes()
    
    print("\n" + "="*60)
    if working:
        print(f"✅ API acessível em: {working[0]}")
    else:
        print("❌ API não acessível")
        print("\nPossíveis causas:")
        print("  1. API não está rodando (reinicie)")
        print("  2. Firewall bloqueando")
        print("  3. Outra aplicação na porta 8001")