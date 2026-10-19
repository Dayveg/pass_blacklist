import pytest
import uuid
from application import create_app
from models.models import db, Blacklist

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'test-secret-key'
    STATIC_BEARER_TOKEN = 'token-estatico-secreto-12345'

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers():
    return {'Authorization': 'Bearer token-estatico-secreto-12345'}

def test_health_check(client):
    """Verifica que los endpoints de Health Check respondan 200 sin autenticación."""
    res_health = client.get('/health')
    assert res_health.status_code == 200
    assert res_health.get_json() == {'status': 'healthy', 'service': 'blacklist-microservice'}

    res_root = client.get('/')
    assert res_root.status_code == 200
    assert res_root.get_json() == {'status': 'healthy', 'service': 'blacklist-microservice'}

def test_missing_auth_header(client):
    """Peticiones sin encabezado de autorización deben retornar 401."""
    payload = {
        'email': 'test@example.com',
        'app_uuid': str(uuid.uuid4()),
        'blocked_reason': 'Prueba'
    }
    response = client.post('/blacklists', json=payload)
    assert response.status_code == 401
    assert 'Token de autorización faltante' in response.get_json()['message']

def test_malformed_auth_header(client):
    """Peticiones con encabezado no Bearer o mal estructurado deben retornar 401."""
    payload = {
        'email': 'test@example.com',
        'app_uuid': str(uuid.uuid4())
    }
    response = client.post('/blacklists', json=payload, headers={'Authorization': 'Basic 12345'})
    assert response.status_code == 401
    assert 'Formato de encabezado inválido' in response.get_json()['message']

def test_invalid_bearer_token(client):
    """Peticiones con Bearer token incorrecto deben retornar 403."""
    payload = {
        'email': 'test@example.com',
        'app_uuid': str(uuid.uuid4())
    }
    response = client.post('/blacklists', json=payload, headers={'Authorization': 'Bearer token-invalido'})
    assert response.status_code == 403
    assert 'Token inválido o no autorizado' in response.get_json()['message']

def test_add_email_success(client, auth_headers):
    """Registrar un email nuevo debe responder 201 y persistir en BD con IP."""
    test_email = 'fraud@domain.com'
    test_uuid = str(uuid.uuid4())
    payload = {
        'email': test_email,
        'app_uuid': test_uuid,
        'blocked_reason': 'Actividad sospechosa detectada'
    }
    response = client.post('/blacklists', json=payload, headers={
        **auth_headers,
        'X-Forwarded-For': '203.0.113.195, 70.41.3.18'
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['email'] == test_email
    assert 'created_at' in data

    # Validar persistencia en base de datos
    entry = Blacklist.query.filter_by(email=test_email).first()
    assert entry is not None
    assert entry.app_uuid == test_uuid
    assert entry.blocked_reason == 'Actividad sospechosa detectada'
    assert entry.ip_address == '203.0.113.195'

def test_add_email_duplicate_conflict(client, auth_headers):
    """Registrar un email ya existente debe retornar 409 Conflict."""
    test_email = 'duplicate@domain.com'
    payload = {
        'email': test_email,
        'app_uuid': str(uuid.uuid4()),
        'blocked_reason': 'Primer bloqueo'
    }
    res1 = client.post('/blacklists', json=payload, headers=auth_headers)
    assert res1.status_code == 201

    res2 = client.post('/blacklists', json=payload, headers=auth_headers)
    assert res2.status_code == 409
    assert 'ya se encuentra en la lista negra global' in res2.get_json()['message']

def test_validation_errors(client, auth_headers):
    """Datos con email inválido o UUID inválido deben retornar 400 Bad Request."""
    # Email inválido
    res_bad_email = client.post('/blacklists', json={
        'email': 'not-an-email',
        'app_uuid': str(uuid.uuid4())
    }, headers=auth_headers)
    assert res_bad_email.status_code == 400
    assert 'email' in res_bad_email.get_json()['errors']

    # UUID inválido
    res_bad_uuid = client.post('/blacklists', json={
        'email': 'valid@domain.com',
        'app_uuid': 'invalid-uuid-format'
    }, headers=auth_headers)
    assert res_bad_uuid.status_code == 400
    assert 'app_uuid' in res_bad_uuid.get_json()['errors']

def test_get_blacklisted_email(client, auth_headers):
    """Consulta de email en lista negra debe indicar si está o no bloqueado con 200 OK."""
    blocked_email = 'target@domain.com'
    reason = 'Chargeback fraud'
    client.post('/blacklists', json={
        'email': blocked_email,
        'app_uuid': str(uuid.uuid4()),
        'blocked_reason': reason
    }, headers=auth_headers)

    # Email existente
    res_found = client.get(f'/blacklists/{blocked_email}', headers=auth_headers)
    assert res_found.status_code == 200
    data_found = res_found.get_json()
    assert data_found['is_blacklisted'] is True
    assert data_found['blocked_reason'] == reason

    # Email no existente
    res_not_found = client.get('/blacklists/clean@domain.com', headers=auth_headers)
    assert res_not_found.status_code == 200
    data_not_found = res_not_found.get_json()
    assert data_not_found['is_blacklisted'] is False
    assert data_not_found['blocked_reason'] is None
