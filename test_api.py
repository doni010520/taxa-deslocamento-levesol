#!/usr/bin/env python3
"""
Script de teste para API de Taxa de Deslocamento
"""

import requests
import json
import time

# URL da API (mude conforme necessário)
API_URL = "http://localhost:7777"

def print_section(title):
    """Imprime seção formatada"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_endpoint(method, endpoint, data=None):
    """Testa um endpoint e mostra resultado"""
    url = f"{API_URL}{endpoint}"
    print(f"\n🔍 Testando: {method} {endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'calculo' in result:
                print(f"   ✅ Distância ida: {result['distancia']['ida_km']}km")
                print(f"   ✅ Valor taxa: R$ {result['calculo']['valor_taxa']}")
                print(f"   ✅ Método: {result['distancia']['metodo_calculo']}")
            else:
                print(f"   ✅ {result.get('status', 'OK')}")
        else:
            error = response.json()
            print(f"   ❌ Erro: {error.get('mensagem', 'Erro desconhecido')}")
            
        return response.json()
        
    except Exception as e:
        print(f"   ❌ Erro na requisição: {e}")
        return None

def run_tests():
    """Executa bateria completa de testes"""
    
    print_section("🚀 TESTE DA API DE TAXA DE DESLOCAMENTO")
    
    # 1. Teste de saúde
    print_section("1. TESTE DE SAÚDE")
    result = test_endpoint("GET", "/health")
    if result:
        print(f"   Cache: {result.get('cache_size', 0)} CEPs")
        print(f"   ViaCEP: {result.get('servicos', {}).get('viacep', 'não testado')}")
        print(f"   OSRM: {result.get('servicos', {}).get('osrm', 'não testado')}")
    
    # 2. Informações da API
    print_section("2. INFORMAÇÕES DA API")
    test_endpoint("GET", "/")
    
    # 3. Testes de cálculo
    print_section("3. TESTES DE CÁLCULO DE TAXA")
    
    casos_teste = [
        ("Marília-SP", "17500-005", "Alta distância"),
        ("Bauru Centro", "17015-321", "Dentro da franquia"),
        ("Agudos-SP", "17120-000", "Próximo ao limite"),
        ("São Paulo-SP", "01310-100", "Capital"),
        ("Botucatu-SP", "18600-000", "Cidade média"),
    ]
    
    for nome, cep, descricao in casos_teste:
        print(f"\n📍 {nome} ({descricao})")
        test_endpoint("POST", "/calcular", {"cep": cep})
        time.sleep(0.5)  # Evitar sobrecarga
    
    # 4. Teste GET rápido
    print_section("4. TESTE ENDPOINT GET")
    test_endpoint("GET", "/teste/17500-005")
    
    # 5. Teste de CEP inválido
    print_section("5. TESTE DE VALIDAÇÃO")
    test_endpoint("POST", "/calcular", {"cep": "123"})
    test_endpoint("POST", "/calcular", {"cep": "99999-999"})
    
    # 6. Limpar cache
    print_section("6. LIMPEZA DE CACHE")
    test_endpoint("POST", "/limpar-cache")
    
    print_section("✅ TESTES CONCLUÍDOS")

if __name__ == "__main__":
    print("🔧 Testando API em:", API_URL)
    print("   Certifique-se que a API está rodando!")
    input("   Pressione ENTER para começar...")
    
    run_tests()
