#!/bin/bash

# Definir a porta padrão se não estiver definida
PORT=${PORT:-8080}

echo "Iniciando aplicação FastAPI com Uvicorn na porta $PORT"
exec uvicorn main:app --host 0.0.0.0 --port $PORT