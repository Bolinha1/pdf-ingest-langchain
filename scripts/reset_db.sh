#!/usr/bin/env bash
set -euo pipefail

echo "Removendo containers e volumes do banco..."
docker compose down -v

echo "Subindo banco limpo..."
docker compose up -d

echo "Banco reiniciado com sucesso."
