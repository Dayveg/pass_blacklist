from flask import request, current_app
from flask_restful import Resource
from marshmallow import ValidationError
from functools import wraps
from models.models import db, Blacklist, BlacklistSchema

blacklist_schema = BlacklistSchema()

def token_required(f):
    """Decorador para validar el Bearer Token estático o dinámico."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header:
            return {'message': 'Token de autorización faltante'}, 401
        
        parts = auth_header.split()
        if parts[0].lower() != 'bearer' or len(parts) != 2:
            return {'message': 'Formato de encabezado inválido. Use: Bearer <token>'}, 401
        
        token = parts[1]
        expected_token = current_app.config['STATIC_BEARER_TOKEN']
        
        if token != expected_token:
            return {'message': 'Token inválido o no autorizado'}, 403
            
        return f(*args, **kwargs)
    return decorated

class BlacklistListResource(Resource):
    @token_required
    def post(self):
        json_data = request.get_json(silent=True)
        if not json_data:
            return {'message': 'Cuerpo de la solicitud vacío o formato JSON inválido'}, 400

        # Validar estructura de entrada (email, UUID válido, max 255 chars en reason)
        try:
            # Validamos con marshmallow sin instanciar aún
            validated_data = blacklist_schema.load(json_data, session=db.session)
        except ValidationError as err:
            return {'message': 'Error de validación en los parámetros', 'errors': err.messages}, 400

        email = json_data.get('email').lower().strip()

        # Verificar si el email ya existe en la lista negra
        existing_entry = Blacklist.query.filter_by(email=email).first()
        if existing_entry:
            return {'message': f'El email {email} ya se encuentra en la lista negra global.'}, 409

        # Capturar IP real (considerando el Load Balancer de AWS Beanstalk)
        if request.headers.getlist("X-Forwarded-For"):
            client_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        else:
            client_ip = request.remote_addr or '127.0.0.1'

        new_blacklist = Blacklist(
            email=email,
            app_uuid=str(json_data.get('app_uuid')),
            blocked_reason=json_data.get('blocked_reason', ''),
            ip_address=client_ip
        )

        try:
            db.session.add(new_blacklist)
            db.session.commit()
            return {
                'message': 'El email ha sido agregado exitosamente a la lista negra global.',
                'email': email,
                'created_at': new_blacklist.created_at.isoformat()
            }, 201
        except Exception as e:
            db.session.rollback()
            return {'message': 'Error interno al persistir en la base de datos', 'detail': str(e)}, 500


class BlacklistDetailResource(Resource):
    @token_required
    def get(self, email):
        clean_email = email.lower().strip()
        entry = Blacklist.query.filter_by(email=clean_email).first()

        if entry:
            return {
                'is_blacklisted': True,
                'blocked_reason': entry.blocked_reason
            }, 200
        else:
            return {
                'is_blacklisted': False,
                'blocked_reason': None
            }, 200


class HealthCheckResource(Resource):
    def get(self):
        """Endpoint para el Health Check de AWS Elastic Beanstalk (No requiere Auth)."""
        return {'status': 'healthy', 'service': 'blacklist-microservice'}, 200
