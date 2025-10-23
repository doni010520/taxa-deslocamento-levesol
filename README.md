# API Taxa de Deslocamento - LEVESOL (Versão Gratuita)

API 100% gratuita para calcular taxa de deslocamento baseada na distância entre CEPs.

## 🆓 Totalmente Gratuito

Esta API utiliza apenas serviços gratuitos:
- **ViaCEP**: Para buscar informações de CEPs
- **Nominatim/OpenStreetMap**: Para obter coordenadas geográficas
- **OSRM**: Para calcular rotas reais de direção

## 🚀 Deploy Rápido no Easypanel

### Passo 1: Fork ou Clone

```bash
git clone https://github.com/SEU_USUARIO/taxa-deslocamento-levesol.git
cd taxa-deslocamento-levesol
```

### Passo 2: Deploy no Easypanel

1. Acesse seu painel Easypanel
2. Clique em **"Create Service"**
3. Escolha **"App"** → **"GitHub"**
4. Configure:
   - **Repository**: seu-repositorio
   - **Branch**: main
   - **Port**: 7777
   - **Health Check Path**: `/health`
5. Deploy! 🎉

## 📡 Endpoints da API

### `GET /`
Retorna informações da API e regras de negócio

### `GET /health`
Status de saúde e verificação dos serviços

### `POST /calcular`
Calcula a taxa de deslocamento

**Request:**
```json
{
  "cep": "17500-005"
}
```

**Response de Sucesso:**
```json
{
  "status": "sucesso",
  "origem": {
    "cep": "17017-337",
    "endereco": "Bauru-SP",
    "coordenadas": {
      "lat": -22.3155,
      "lon": -49.0708
    }
  },
  "destino": {
    "cep": "17500-005",
    "endereco": "Marília-SP",
    "coordenadas": {
      "lat": -22.4249,
      "lon": -49.9461
    }
  },
  "distancia": {
    "ida_km": 107.5,
    "ida_volta_km": 215.0,
    "tempo_estimado_ida_minutos": 95,
    "metodo_calculo": "osrm"
  },
  "calculo": {
    "franquia_km_ida": 30,
    "franquia_km_total": 60,
    "km_excedente": 155.0,
    "taxa_por_km": 1.6,
    "valor_taxa": 248.0
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

### `GET /teste/{cep}`
Teste rápido via GET

Exemplo: `GET /teste/17500-005`

### `POST /limpar-cache`
Limpa o cache de coordenadas armazenadas

## 🧮 Regras de Negócio

- **CEP Origem**: 17017-337 (Levesol - Bauru/SP)
- **Franquia**: 30km na ida (60km total ida+volta)
- **Taxa**: R$ 1,60 por km excedente
- **Fórmula**: `(Distância_Total_KM - 60) × R$ 1,60`

## 💻 Desenvolvimento Local

### Sem Docker:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Com Docker:
```bash
docker-compose up --build
```

Acesse: http://localhost:7777

## 🔌 Integração com n8n

### Node HTTP Request:
```javascript
{
  "method": "POST",
  "url": "https://seu-dominio.easypanel.host/calcular",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "cep": "{{$json.cep_cliente}}"
  }
}
```

### Exemplo de uso no JavaScript do n8n:
```javascript
const cep_cliente = "17500-005";

const response = await fetch('https://seu-app.easypanel.host/calcular', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ cep: cep_cliente })
});

const data = await response.json();

if (data.status === 'sucesso') {
  const valor_taxa = data.calculo.valor_taxa;
  // Adicionar taxa ao valor total
}
```

## 📊 Exemplos de Resposta

### CEP dentro da franquia (sem taxa):
```json
{
  "calculo": {
    "km_excedente": 0,
    "valor_taxa": 0
  }
}
```

### CEP fora da franquia (com taxa):
```json
{
  "calculo": {
    "km_excedente": 155.0,
    "valor_taxa": 248.0
  }
}
```

## 🎯 Precisão

- **OSRM**: ~95% de precisão (rotas reais)
- **Haversine**: ~85% de precisão (linha reta × 1.3)
- **Fallback automático**: Se OSRM falhar, usa Haversine

## ⚡ Performance

- Cache de coordenadas para reduzir chamadas
- Timeout configurado para evitar travamentos
- Health check para monitoramento

## 🐛 Troubleshooting

### Erro: CEP_INVALIDO
- Verifique se o CEP tem 8 dígitos
- Formatos aceitos: 17500-005 ou 17500005

### Erro: ERRO_CALCULO
- CEP pode não existir no ViaCEP
- Serviços externos podem estar offline

### Método de cálculo "haversine_ajustado"
- OSRM estava indisponível
- Resultado é aproximado (mas ainda útil)

## 📝 Logs

A aplicação gera logs detalhados:
```
2024-01-15 10:30:00 - INFO - Buscando CEP 17500005 no ViaCEP...
2024-01-15 10:30:01 - INFO - Consultando OSRM para calcular rota...
2024-01-15 10:30:02 - INFO - Distância excede franquia. Taxa: R$ 248.00
```

## 🤝 Suporte

Desenvolvido para LEVESOL - Sistema de Energia Solar

---

**Versão**: 1.0.0-free | **Licença**: MIT
