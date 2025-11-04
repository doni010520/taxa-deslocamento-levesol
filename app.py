from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import logging
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# --- CONSTANTES DA REGRA DE NEGÓCIO ---
CEP_ORIGEM = "17017-337"  # CEP da Levesol em Bauru
TAXA_POR_KM = 1.60
FRANQUIA_KM_IDA = 30.0
FRANQUIA_KM_TOTAL = FRANQUIA_KM_IDA * 2

# Cache de coordenadas para evitar múltiplas chamadas
CACHE_COORDENADAS = {}

def limpar_cep(cep: str) -> str:
    """Remove caracteres não numéricos do CEP"""
    return ''.join(filter(str.isdigit, cep))

def formatar_cep(cep: str) -> str:
    """Formata CEP para o padrão XXXXX-XXX"""
    cep_limpo = limpar_cep(cep)
    if len(cep_limpo) == 8:
        return f"{cep_limpo[:5]}-{cep_limpo[5:]}"
    return cep

def obter_coordenadas_viacep(cep: str) -> dict:
    """
    Obtém coordenadas aproximadas do CEP usando ViaCEP + Nominatim
    """
    cep_limpo = limpar_cep(cep)
    
    # Verificar cache
    if cep_limpo in CACHE_COORDENADAS:
        logger.info(f"CEP {cep_limpo} encontrado no cache")
        return CACHE_COORDENADAS[cep_limpo]
    
    try:
        # 1. Buscar dados do CEP no ViaCEP
        logger.info(f"Buscando CEP {cep_limpo} no ViaCEP...")
        viacep_url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        response = requests.get(viacep_url, timeout=5)
        
        if response.status_code != 200:
            raise Exception(f"CEP não encontrado: {cep}")
        
        dados_cep = response.json()
        
        if 'erro' in dados_cep:
            raise Exception(f"CEP inválido: {cep}")
        
        # 2. Tentar buscar coordenadas usando Nominatim (OpenStreetMap)
        logger.info(f"Buscando coordenadas para {dados_cep['localidade']}-{dados_cep['uf']}")
        
        # Primeiro tentar com endereço completo se tiver logradouro
        if dados_cep.get('logradouro'):
            endereco_busca = f"{dados_cep['logradouro']}, {dados_cep['bairro']}, {dados_cep['localidade']}, {dados_cep['uf']}, Brazil"
        else:
            # Se não tiver logradouro, usar só cidade
            endereco_busca = f"{dados_cep['localidade']}, {dados_cep['uf']}, Brazil"
        
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': endereco_busca,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'br'
        }
        headers = {
            'User-Agent': 'LeveSol-Taxa-Deslocamento/1.0 (contato@levesol.com.br)'
        }
        
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200 and response.json():
            coords_data = response.json()[0]
            resultado = {
                'lat': float(coords_data['lat']),
                'lon': float(coords_data['lon']),
                'endereco': f"{dados_cep.get('logradouro', '')}, {dados_cep['bairro']}, {dados_cep['localidade']}-{dados_cep['uf']}".strip(', '),
                'cidade': dados_cep['localidade'],
                'uf': dados_cep['uf']
            }
            
            # Guardar no cache
            CACHE_COORDENADAS[cep_limpo] = resultado
            logger.info(f"Coordenadas encontradas via Nominatim: {resultado['lat']}, {resultado['lon']}")
            return resultado
        
        # Se Nominatim falhar, tentar busca só pela cidade
        logger.info("Tentando busca só pela cidade...")
        params['q'] = f"{dados_cep['localidade']}, {dados_cep['uf']}, Brazil"
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200 and response.json():
            coords_data = response.json()[0]
            resultado = {
                'lat': float(coords_data['lat']),
                'lon': float(coords_data['lon']),
                'endereco': f"{dados_cep['localidade']}-{dados_cep['uf']}",
                'cidade': dados_cep['localidade'],
                'uf': dados_cep['uf']
            }
            CACHE_COORDENADAS[cep_limpo] = resultado
            logger.info(f"Coordenadas da cidade encontradas: {resultado['lat']}, {resultado['lon']}")
            return resultado
        
        # Fallback: usar coordenadas conhecidas para cidades principais
        coordenadas_cidades = {
            # Bauru e região
            "17": {"lat": -22.3155, "lon": -49.0708},  # Bauru (padrão para 17xxx)
            "17017": {"lat": -22.3155, "lon": -49.0708},  # Bauru
            "17015": {"lat": -22.3155, "lon": -49.0708},  # Bauru Centro
            "17120": {"lat": -22.2189, "lon": -49.0478},  # Agudos
            "17500": {"lat": -22.4249, "lon": -49.9461},  # Marília
            "17600": {"lat": -22.2208, "lon": -50.1761},  # Tupã
            "17800": {"lat": -21.6833, "lon": -51.1333},  # Adamantina
            "18600": {"lat": -22.8858, "lon": -48.4452},  # Botucatu
            # São Paulo capital
            "01310": {"lat": -23.5489, "lon": -46.6388},  # Av Paulista
            "01000": {"lat": -23.5505, "lon": -46.6333},  # São Paulo Centro
            # Outras capitais
            "80000": {"lat": -25.4284, "lon": -49.2733},  # Curitiba
            "30000": {"lat": -19.9167, "lon": -43.9345},  # Belo Horizonte
        }
        
        # Tentar com prefixo de 5 dígitos
        prefixo5 = cep_limpo[:5]
        if prefixo5 in coordenadas_cidades:
            coords = coordenadas_cidades[prefixo5]
        # Tentar com prefixo de 2 dígitos
        elif cep_limpo[:2] in coordenadas_cidades:
            coords = coordenadas_cidades[cep_limpo[:2]]
        else:
            raise Exception(f"Não foi possível obter coordenadas para o CEP {cep}")
        
        resultado = {
            'lat': coords['lat'],
            'lon': coords['lon'],
            'endereco': f"{dados_cep['localidade']}-{dados_cep['uf']} (aproximado)",
            'cidade': dados_cep['localidade'],
            'uf': dados_cep['uf']
        }
        
        CACHE_COORDENADAS[cep_limpo] = resultado
        logger.info(f"Usando coordenadas aproximadas: {resultado['lat']}, {resultado['lon']}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao obter coordenadas: {e}")
        raise

def obter_coordenadas_por_endereco(endereco_completo: str) -> dict:
    """
    Obtém coordenadas diretamente do endereço usando Nominatim
    Aceita endereço em formato livre
    """
    # Verificar cache (usando endereço como chave)
    cache_key = f"endereco_{endereco_completo.lower().strip()}"
    if cache_key in CACHE_COORDENADAS:
        logger.info(f"Endereço '{endereco_completo}' encontrado no cache")
        return CACHE_COORDENADAS[cache_key]
    
    try:
        logger.info(f"Buscando coordenadas para endereço: {endereco_completo}")
        
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        
        # Adicionar Brazil ao final se não tiver
        endereco_busca = endereco_completo
        if "brazil" not in endereco_completo.lower() and "brasil" not in endereco_completo.lower():
            endereco_busca = endereco_completo + ", Brazil"
        
        params = {
            'q': endereco_busca,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'br',
            'addressdetails': 1  # Retorna detalhes do endereço
        }
        headers = {
            'User-Agent': 'LeveSol-Taxa-Deslocamento/1.0 (contato@levesol.com.br)'
        }
        
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=5)
        
        if response.status_code != 200 or not response.json():
            raise Exception(f"Endereço não encontrado: {endereco_completo}")
        
        resultado_busca = response.json()[0]
        address = resultado_busca.get('address', {})
        
        # Extrair cidade (pode vir em diferentes campos)
        cidade = (
            address.get('city') or 
            address.get('town') or 
            address.get('municipality') or 
            address.get('village') or 
            address.get('county') or
            ''
        )
        
        # Extrair UF
        uf = address.get('state', '')
        
        # Extrair CEP se disponível
        cep = address.get('postcode', 'N/A')
        
        resultado = {
            'lat': float(resultado_busca['lat']),
            'lon': float(resultado_busca['lon']),
            'endereco': resultado_busca.get('display_name', endereco_completo),
            'cidade': cidade,
            'uf': uf,
            'cep': cep
        }
        
        # Guardar no cache
        CACHE_COORDENADAS[cache_key] = resultado
        
        logger.info(f"Coordenadas encontradas: {resultado['lat']}, {resultado['lon']}")
        logger.info(f"Localização identificada: {cidade} - {uf}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao obter coordenadas por endereço: {e}")
        raise

def calcular_distancia_osrm(coord_origem: dict, coord_destino: dict) -> dict:
    """
    Calcula distância real de direção usando OSRM (Open Source Routing Machine)
    """
    try:
        # Usar servidor público do OSRM
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coord_origem['lon']},{coord_origem['lat']};{coord_destino['lon']},{coord_destino['lat']}"
        
        params = {
            'overview': 'false',
            'alternatives': 'false',
            'steps': 'false'
        }
        
        logger.info(f"Consultando OSRM para calcular rota...")
        response = requests.get(osrm_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['code'] == 'Ok' and data['routes']:
                route = data['routes'][0]
                logger.info(f"Rota OSRM calculada: {route['distance']/1000:.2f}km")
                return {
                    'distancia_metros': route['distance'],
                    'duracao_segundos': route['duration'],
                    'metodo': 'osrm'
                }
        
        # Se OSRM falhar, usar Haversine
        logger.warning("OSRM falhou, usando cálculo Haversine")
        return calcular_distancia_haversine(coord_origem, coord_destino)
        
    except Exception as e:
        logger.warning(f"Erro no OSRM: {e}, usando Haversine")
        return calcular_distancia_haversine(coord_origem, coord_destino)

def calcular_distancia_haversine(coord_origem: dict, coord_destino: dict) -> dict:
    """
    Calcula distância em linha reta (Haversine) como fallback
    Multiplica por 1.3 para aproximar distância real de estrada
    """
    R = 6371000  # Raio da Terra em metros
    
    lat1, lon1 = radians(coord_origem['lat']), radians(coord_origem['lon'])
    lat2, lon2 = radians(coord_destino['lat']), radians(coord_destino['lon'])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distancia_linha_reta = R * c
    
    # Multiplicar por 1.3 para aproximar distância real de estrada
    distancia_estimada = distancia_linha_reta * 1.3
    
    # Estimar tempo (média de 80 km/h)
    tempo_segundos = (distancia_estimada / 1000) * 3600 / 80
    
    logger.info(f"Distância Haversine calculada: {distancia_estimada/1000:.2f}km")
    
    return {
        'distancia_metros': distancia_estimada,
        'duracao_segundos': tempo_segundos,
        'metodo': 'haversine_ajustado'
    }

def calcular_taxa_por_endereco(endereco_destino: str) -> dict:
    """
    Calcula taxa de deslocamento usando endereço diretamente
    """
    try:
        logger.info(f"=== Iniciando cálculo de taxa por endereço ===")
        logger.info(f"Endereço Destino: {endereco_destino}")
        
        # Obter coordenadas da origem (Levesol - Bauru)
        coord_origem = obter_coordenadas_viacep(CEP_ORIGEM)
        
        # Obter coordenadas do endereço de destino
        coord_destino = obter_coordenadas_por_endereco(endereco_destino)
        
        # Calcular distância
        resultado_distancia = calcular_distancia_osrm(coord_origem, coord_destino)
        
        distancia_ida_km = resultado_distancia['distancia_metros'] / 1000
        duracao_minutos = resultado_distancia['duracao_segundos'] / 60
        
        # Calcular taxa
        valor_taxa = 0.0
        km_excedente = 0.0
        
        if distancia_ida_km > FRANQUIA_KM_IDA:
            distancia_total_km = distancia_ida_km * 2
            km_excedente = distancia_total_km - FRANQUIA_KM_TOTAL
            valor_taxa = km_excedente * TAXA_POR_KM
            logger.info(f"Distância excede franquia. Taxa: R$ {valor_taxa:.2f}")
        else:
            logger.info(f"Distância dentro da franquia. Sem taxa adicional.")
        
        resultado = {
            "status": "sucesso",
            "origem": {
                "cep": CEP_ORIGEM,
                "endereco": coord_origem['endereco'],
                "coordenadas": {
                    "lat": coord_origem['lat'],
                    "lon": coord_origem['lon']
                }
            },
            "destino": {
                "endereco_informado": endereco_destino,
                "endereco_encontrado": coord_destino['endereco'],
                "cidade": coord_destino['cidade'],
                "uf": coord_destino['uf'],
                "cep": coord_destino['cep'],
                "coordenadas": {
                    "lat": coord_destino['lat'],
                    "lon": coord_destino['lon']
                }
            },
            "distancia": {
                "ida_km": round(distancia_ida_km, 2),
                "ida_volta_km": round(distancia_ida_km * 2, 2),
                "tempo_estimado_ida_minutos": round(duracao_minutos, 0),
                "metodo_calculo": resultado_distancia['metodo']
            },
            "calculo": {
                "franquia_km_ida": FRANQUIA_KM_IDA,
                "franquia_km_total": FRANQUIA_KM_TOTAL,
                "km_excedente": round(km_excedente, 2),
                "taxa_por_km": TAXA_POR_KM,
                "valor_taxa": round(valor_taxa, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"=== Cálculo concluído com sucesso ===")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao calcular taxa: {e}")
        return {
            "status": "erro",
            "codigo": "ERRO_CALCULO",
            "mensagem": str(e)
        }

def calcular_taxa_deslocamento(cep_destino: str) -> dict:
    """
    Calcula taxa de deslocamento usando CEP (mantido para compatibilidade)
    """
    try:
        cep_destino_formatado = formatar_cep(cep_destino)
        
        # Obter coordenadas dos CEPs
        logger.info(f"=== Iniciando cálculo de taxa ===")
        logger.info(f"CEP Origem: {CEP_ORIGEM}")
        logger.info(f"CEP Destino: {cep_destino_formatado}")
        
        coord_origem = obter_coordenadas_viacep(CEP_ORIGEM)
        coord_destino = obter_coordenadas_viacep(cep_destino)
        
        # Calcular distância
        resultado_distancia = calcular_distancia_osrm(coord_origem, coord_destino)
        
        distancia_ida_km = resultado_distancia['distancia_metros'] / 1000
        duracao_minutos = resultado_distancia['duracao_segundos'] / 60
        
        # Calcular taxa
        valor_taxa = 0.0
        km_excedente = 0.0
        
        if distancia_ida_km > FRANQUIA_KM_IDA:
            distancia_total_km = distancia_ida_km * 2
            km_excedente = distancia_total_km - FRANQUIA_KM_TOTAL
            valor_taxa = km_excedente * TAXA_POR_KM
            logger.info(f"Distância excede franquia. Taxa: R$ {valor_taxa:.2f}")
        else:
            logger.info(f"Distância dentro da franquia. Sem taxa adicional.")
        
        resultado = {
            "status": "sucesso",
            "origem": {
                "cep": CEP_ORIGEM,
                "endereco": coord_origem['endereco'],
                "coordenadas": {
                    "lat": coord_origem['lat'],
                    "lon": coord_origem['lon']
                }
            },
            "destino": {
                "cep": cep_destino_formatado,
                "endereco": coord_destino['endereco'],
                "coordenadas": {
                    "lat": coord_destino['lat'],
                    "lon": coord_destino['lon']
                }
            },
            "distancia": {
                "ida_km": round(distancia_ida_km, 2),
                "ida_volta_km": round(distancia_ida_km * 2, 2),
                "tempo_estimado_ida_minutos": round(duracao_minutos, 0),
                "metodo_calculo": resultado_distancia['metodo']
            },
            "calculo": {
                "franquia_km_ida": FRANQUIA_KM_IDA,
                "franquia_km_total": FRANQUIA_KM_TOTAL,
                "km_excedente": round(km_excedente, 2),
                "taxa_por_km": TAXA_POR_KM,
                "valor_taxa": round(valor_taxa, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"=== Cálculo concluído com sucesso ===")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao calcular taxa: {e}")
        return {
            "status": "erro",
            "codigo": "ERRO_CALCULO",
            "mensagem": str(e)
        }

# --- ROTAS DA API ---

@app.route('/')
def home():
    """Rota raiz com informações da API"""
    return jsonify({
        "api": "Calculadora de Taxa de Deslocamento - LEVESOL",
        "versao": "2.0.0-endereco",
        "endpoints": {
            "/": "Informações da API",
            "/health": "Status de saúde",
            "/calcular": "POST - Calcular taxa de deslocamento (aceita 'endereco' ou 'cep')",
            "/teste/<cep>": "GET - Testar cálculo com CEP",
            "/teste-endereco/<endereco>": "GET - Testar cálculo com endereço",
            "/limpar-cache": "POST - Limpar cache de coordenadas"
        },
        "servicos_utilizados": {
            "cep": "ViaCEP (gratuito)",
            "geocoding": "Nominatim/OpenStreetMap (gratuito)",
            "routing": "OSRM - Open Source Routing Machine (gratuito)"
        },
        "regras_negocio": {
            "cep_origem": CEP_ORIGEM,
            "franquia_km_ida": FRANQUIA_KM_IDA,
            "franquia_km_total": FRANQUIA_KM_TOTAL,
            "taxa_por_km": f"R$ {TAXA_POR_KM}",
            "formula": "(Distância_Total_KM - 60) × R$ 1,60"
        },
        "exemplo_uso_endereco": {
            "descricao": "Enviar endereço completo em formato livre",
            "exemplos": [
                "Avenida Paulista, 1000, São Paulo, SP",
                "Rua XV de Novembro, Marília",
                "Praça da Sé, São Paulo"
            ]
        },
        "observacoes": [
            "NOVIDADE: Agora aceita endereço completo (não precisa mais de CEP!)",
            "Distâncias calculadas por rota rodoviária quando disponível",
            "Fallback para cálculo aproximado se serviço OSRM estiver indisponível",
            "Endereços e CEPs são cacheados para melhor performance"
        ]
    })

@app.route('/health')
def health():
    """Verificação de saúde da aplicação"""
    status = {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(CACHE_COORDENADAS),
        "servicos": {}
    }
    
    # Testar ViaCEP
    try:
        r = requests.get("https://viacep.com.br/ws/01310100/json/", timeout=2)
        status["servicos"]["viacep"] = "operacional" if r.status_code == 200 else "com problema"
    except:
        status["servicos"]["viacep"] = "inacessível"
    
    # Testar Nominatim
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search?q=São+Paulo&format=json&limit=1", 
                        headers={'User-Agent': 'LeveSol-Taxa-Deslocamento/1.0'}, timeout=2)
        status["servicos"]["nominatim"] = "operacional" if r.status_code == 200 else "com problema"
    except:
        status["servicos"]["nominatim"] = "inacessível"
    
    # Testar OSRM
    try:
        r = requests.get("http://router.project-osrm.org/route/v1/driving/-49.0708,-22.3155;-46.6388,-23.5489?overview=false", timeout=2)
        status["servicos"]["osrm"] = "operacional" if r.status_code == 200 else "com problema"
    except:
        status["servicos"]["osrm"] = "inacessível"
    
    return jsonify(status)

@app.route('/calcular', methods=['POST'])
def calcular():
    """
    Endpoint principal para calcular taxa de deslocamento
    
    Body JSON - Opção 1 (RECOMENDADO - Endereço completo):
    {
        "endereco": "Avenida Paulista, 1000, São Paulo, SP"
    }
    
    Body JSON - Opção 2 (Compatibilidade - CEP):
    {
        "cep": "17500-005"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "erro",
                "codigo": "DADOS_OBRIGATORIOS",
                "mensagem": "Informe o endereço ou CEP no corpo da requisição",
                "exemplo_endereco": {
                    "endereco": "Avenida Paulista, 1000, São Paulo, SP"
                },
                "exemplo_cep": {
                    "cep": "17500-005"
                }
            }), 400
        
        # Verificar se foi enviado endereço ou CEP
        if 'endereco' in data:
            endereco = data['endereco'].strip()
            
            if not endereco:
                return jsonify({
                    "status": "erro",
                    "codigo": "ENDERECO_VAZIO",
                    "mensagem": "O endereço não pode estar vazio"
                }), 400
            
            # Calcular usando endereço
            resultado = calcular_taxa_por_endereco(endereco)
            
        elif 'cep' in data:
            # Manter compatibilidade com CEP
            cep = data['cep']
            cep_limpo = limpar_cep(cep)
            
            if len(cep_limpo) != 8:
                return jsonify({
                    "status": "erro",
                    "codigo": "CEP_INVALIDO",
                    "mensagem": f"CEP inválido: {cep}. Use formato XXXXX-XXX ou XXXXXXXX"
                }), 400
            
            resultado = calcular_taxa_deslocamento(cep)
        else:
            return jsonify({
                "status": "erro",
                "codigo": "PARAMETRO_INVALIDO",
                "mensagem": "Informe 'endereco' ou 'cep' no corpo da requisição",
                "exemplo": {
                    "endereco": "Rua XV de Novembro, Marília, SP"
                }
            }), 400
        
        # Retornar com status HTTP apropriado
        if resultado['status'] == 'erro':
            return jsonify(resultado), 400
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Erro no endpoint /calcular: {e}")
        return jsonify({
            "status": "erro",
            "codigo": "ERRO_SERVIDOR",
            "mensagem": "Erro interno do servidor"
        }), 500

@app.route('/teste/<cep>')
def teste(cep):
    """
    Endpoint GET para testes rápidos com CEP
    Exemplo: /teste/17500-005
    """
    resultado = calcular_taxa_deslocamento(cep)
    
    if resultado['status'] == 'erro':
        return jsonify(resultado), 400
    
    return jsonify(resultado), 200

@app.route('/teste-endereco/<path:endereco>')
def teste_endereco(endereco):
    """
    Endpoint GET para testes rápidos com endereço
    Exemplos: 
    - /teste-endereco/Avenida Paulista, São Paulo
    - /teste-endereco/Rua XV de Novembro, 123, Marília, SP
    """
    resultado = calcular_taxa_por_endereco(endereco)
    
    if resultado['status'] == 'erro':
        return jsonify(resultado), 400
    
    return jsonify(resultado), 200

@app.route('/limpar-cache', methods=['POST'])
def limpar_cache():
    """Limpa o cache de coordenadas"""
    global CACHE_COORDENADAS
    tamanho_anterior = len(CACHE_COORDENADAS)
    CACHE_COORDENADAS = {}
    
    return jsonify({
        "status": "sucesso",
        "mensagem": f"Cache limpo. {tamanho_anterior} entradas removidas.",
        "timestamp": datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "erro",
        "codigo": "ENDPOINT_NAO_ENCONTRADO",
        "mensagem": "Endpoint não encontrado. Consulte / para ver endpoints disponíveis"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "status": "erro",
        "codigo": "ERRO_INTERNO",
        "mensagem": "Erro interno do servidor"
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 7777))
    logger.info(f"Iniciando servidor na porta {port}")
    logger.info(f"Versão 2.0 - Suporte a cálculo por ENDEREÇO!")
    app.run(host='0.0.0.0', port=port, debug=False)
