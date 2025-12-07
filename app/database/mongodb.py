# test_env.py

import os

from dotenv import load_dotenv
from pymongo import MongoClient

# Carga el archivo .env desde la ubicación actual
load_dotenv()

print('🔍 Variables cargadas desde .env:')
print(f'MONGODB_URI: {os.getenv("MONGODB_URI", "NO ENCONTRADA")}')
print(f'DATABASE_NAME: {os.getenv("DATABASE_NAME", "NO ENCONTRADA")}')

# Listar todas
print('\n📋 Todas las variables:')
for key, value in os.environ.items():
    if 'MONGODB' in key.upper() or 'DATABASE' in key.upper():
        print(f'{key}: {value[:50]}...')  # Muestra solo primeros 50 chars

print(MongoClient(os.getenv('MONGODB_URI')).server_info())
