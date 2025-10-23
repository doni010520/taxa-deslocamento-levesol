FROM python:3.11-slim

# Diretório de trabalho
WORKDIR /app

# Copiar arquivos de requisitos
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Expor porta
EXPOSE 7777

# Comando para executar a aplicação com Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7777", "--workers", "2", "--threads", "2", "--timeout", "30", "--log-level", "info", "app:app"]
