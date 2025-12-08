# app/database/connection.py

import os

from dotenv import load_dotenv
from pymongo import MongoClient

# Carga el archivo .env desde la ubicación actual
load_dotenv()

def get_database():
    """Retorna la base de datos de SecuBot"""
    client = MongoClient(
        os.getenv("MONGODB_URI"),
        serverSelectionTimeoutMS=5000
    )
    db_name = os.getenv("DATABASE_NAME", "secubot_dev")
    return client[db_name]

