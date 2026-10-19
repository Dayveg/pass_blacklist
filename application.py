from flask import Flask
from flask_restful import Api
from flask_jwt_extended import JWTManager
from config import Config
from models.models import db, ma
from views.views import BlacklistListResource, BlacklistDetailResource, HealthCheckResource

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones
    db.init_app(app)
    ma.init_app(app)
    jwt = JWTManager(app)
    api = Api(app)

    # Crear tablas en la base de datos automáticamente al iniciar
    with app.app_context():
        db.create_all()

    # Registro de rutas según especificación exacta
    api.add_resource(BlacklistListResource, '/blacklists')
    api.add_resource(BlacklistDetailResource, '/blacklists/<string:email>')
    api.add_resource(HealthCheckResource, '/health', '/')

    return app

# AWS Elastic Beanstalk busca por defecto una variable llamada 'application'
application = create_app()

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5000, debug=True)
