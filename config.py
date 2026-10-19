import os

class Config:
    # Conexión a Base de Datos (RDS PostgreSQL o fallback local)
    DB_USER = os.environ.get('RDS_USERNAME', 'postgres')
    DB_PASSWORD = os.environ.get('RDS_PASSWORD', 'postgres')
    DB_HOST = os.environ.get('RDS_HOSTNAME', 'localhost')
    DB_PORT = os.environ.get('RDS_PORT', '5432')
    DB_NAME = os.environ.get('RDS_DB_NAME', 'blacklist_db')

    if os.environ.get('RDS_HOSTNAME'):
        SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    elif os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///blacklist_local.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración JWT y Token Estático predefinido
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret-uniandes-key-2026')
    STATIC_BEARER_TOKEN = os.environ.get('STATIC_BEARER_TOKEN', 'token-estatico-secreto-12345')
