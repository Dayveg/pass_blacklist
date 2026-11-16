# Blacklist Microservice

Microservicio REST en Flask para gestión de listas negras globales, con pruebas unitarias automatizadas (`pytest`), contenerización en Docker, infraestructura definida en Terraform y pipeline CI/CD sobre AWS (CodePipeline, CodeBuild, Amazon ECR y ECS Fargate).

---

## 1. Estructura del Repositorio

```plaintext
pass_blacklist/
├── application.py               # Entry point WSGI de la aplicacion Flask
├── config.py                    # Configuracion de base de datos y tokens
├── models/
│   └── models.py                # Modelo SQLAlchemy (Blacklist) y esquema Marshmallow
├── views/
│   └── views.py                 # Endpoints REST, autenticacion Bearer y /health
├── tests/
│   └── test_blacklist.py        # 8 pruebas unitarias con SQLite en memoria
├── postman/
│   ├── Blacklist_API.postman_collection.json
│   └── Blacklist_Environment.postman_environment.json
├── terraform/                   # IaC para ECR, ECS Fargate, ALB, Target Group y SGs
│   ├── main.tf
│   ├── ecr_iam.tf
│   ├── alb.tf
│   ├── ecs.tf
│   └── outputs.tf
├── Dockerfile                   # Imagen python:3.11-slim + Gunicorn (:5000)
├── buildspec.yml                # Especificacion de AWS CodeBuild (CI)
├── taskdef.json                 # Plantilla de Task Definition para ECS Fargate
├── appspec.yaml                 # Especificacion de despliegue para ECS / CodeDeploy
├── .ebextensions/               # Configuracion de soporte para Elastic Beanstalk
├── Procfile
├── pytest.ini
└── requirements.txt
```

---

## 2. Endpoints de la API

| Método | Endpoint | Autenticación | Código Éxito | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` o `/` | No | `200 OK` | Verificación de salud para el Application Load Balancer |
| `POST` | `/blacklists` | Bearer Token | `201 Created` | Registra un correo en la lista negra |
| `GET` | `/blacklists/<email>` | Bearer Token | `200 OK` | Consulta si un correo está bloqueado |

---

## 3. Ejecución Local y Pruebas

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux / macOS:      source .venv/bin/activate

pip install -r requirements.txt pytest
pytest tests/ -v
```

Para iniciar el servidor en local sobre SQLite (`http://localhost:5000`):

```bash
python application.py
```

---

## 4. Contenedores, CI/CD e Infraestructura en AWS

* **Docker (`Dockerfile`):** Usa `public.ecr.aws/docker/library/python:3.11-slim`, instala dependencias y ejecuta `gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 application:application`.
* **CI (`buildspec.yml`):** Ejecuta `pytest tests/ -v` en `pre_build` con `on-failure: ABORT` para detener la compilación si falla alguna prueba. Si pasa, construye la imagen Docker, la publica en Amazon ECR y genera `imagedefinitions.json` e `imageDetail.json`.
* **IaC (`terraform/`):** Provisiona el repositorio ECR (`blacklist-microservice`), clúster ECS (`blacklist-cluster`), servicio Fargate (`blacklist-service`), Application Load Balancer (`blacklist-alb`) y Target Group tipo `ip` (`blacklist-tg` sobre `/health`).

---

> *Nota: Este README contó con apoyo de herramientas de inteligencia artificial únicamente para la revisión de ortografía y estructura.*
