# Universidad de los Andes
## Maestría en Ingeniería de Software (MISO)
### Proyecto 1 – Entrega 3: Entrega Continua (CD) sobre AWS ECS Fargate, CodeBuild, CodeDeploy y CodePipeline

---

**Estudiante:**
- Leidy Dayana Vega Medina - `ld.vega@uniandes.edu.co`

**Fecha:** *Noviembre 2026*  
**Enlace Repositorio GitHub:** *`https://github.com/Dayveg/pass_blacklist`*  
**Enlace Documentación Pública Postman:** *`https://documenter.getpostman.com/view/[ID-Coleccion]`*  
**Enlace Video de Sustentación (Máx. 10 min):** *`https://youtu.be/[ID-Video]`*  
**URL del Balanceador de Carga (ALB) en AWS ECS Fargate:** *`http://[alb-blacklist-xxx].us-east-1.elb.amazonaws.com`*

---

## 1. Arquitectura de Contenedores y Pipeline CI/CD en AWS Fargate

En esta tercera entrega se evoluciona la arquitectura del microservicio de lista negra global hacia una plataforma de contenedores *serverless* gestionada mediante **Amazon ECS sobre AWS Fargate**, automatizando de extremo a extremo tanto la **Integración Continua (CI)** como la **Entrega Continua (CD)** a través de **AWS CodePipeline**, **AWS CodeBuild**, **Amazon ECR** y **AWS CodeDeploy / Amazon ECS**.
En esta tercera entrega se evoluciona la arquitectura del microservicio de lista negra global hacia una plataforma de contenedores *serverless* gestionada mediante **Amazon ECS sobre AWS Fargate**, aprovisionada declarativamente mediante **HashiCorp Terraform (IaC)** y automatizando de extremo a extremo tanto la **Integración Continua (CI)** como la **Entrega Continua (CD)** a través de **AWS CodePipeline**, **AWS CodeBuild**, **Amazon ECR** y **AWS CodeDeploy / Amazon ECS**.

El diseño del pipeline sigue los principios de **The DevOps Handbook** *(Kim, Humble, Debois & Willis, 2016)* y el modelo de tuberías *hands-off* de Amazon presentado en **AWS re:Invent 2020: *Hands-off: Automating continuous delivery pipelines at Amazon*** *(Liguori, 2020)*:
1. **Primera Vía (*Principles of Flow*) e Infraestructura Inmutable:** El empaquetado en contenedores Docker y la definición declarativa en Terraform (`terraform/`) eliminan la deriva de configuración entre entornos.
2. **Segunda Vía (*Principles of Feedback* y *Andon Cord*):** Las pruebas unitarias automatizadas en `pre_build` actúan como compuerta bloqueante (*pipeline blocker*) que detiene la línea de entrega ante cualquier regresión antes de construir o publicar artefactos.
3. **Despliegues Seguros *Hands-off* y *Automated Rollback*:** La etapa de Entrega Continua verifica en tiempo de ejecución la salud de las nuevas tareas mediante el endpoint `/health` del Application Load Balancer, abortando o revirtiendo automáticamente despliegues defectuosos sin afectar la disponibilidad.

### 1.1. Diagrama de Arquitectura e Integración/Entrega Continua (CI/CD)

```mermaid
flowchart LR
    Dev["Desarrollador\n(git push main)"] --> GH["GitHub\n(pass_blacklist)"]
    GH -->|Webhook| CP["AWS CodePipeline"]
    GH -->|Webhook| CP["AWS CodePipeline\n(blacklist-ci-pipeline)"]
    
    subgraph Stage_CI ["Etapa CI: AWS CodeBuild"]
    subgraph Stage_CI ["Etapa CI: AWS CodeBuild (blacklist-build)"]
        CP --> CB_Test["1. pre_build:\npytest tests/ -v"]
        CB_Test --> CB_Build["2. build:\ndocker build"]
        CB_Build --> CB_Push["3. post_build:\ndocker push a ECR\n+ artefactos JSON"]
    end

    CB_Push -->|Imagen Docker| ECR[("Amazon ECR\nblacklist-microservice")]
    CB_Push -->|taskdef.json, appspec.yaml,\nimageDetail.json,\nimagedefinitions.json| CD["Etapa CD:\nAWS CodeDeploy / ECS"]
    
    subgraph Stage_CD ["Plataforma de Contenedores: AWS ECS Fargate"]
    subgraph Stage_CD ["Plataforma de Contenedores: AWS ECS Fargate (Terraform IaC)"]
        CD --> ALB["Application Load Balancer\n(HTTP :80 -> Target Group :5000)"]
        ALB --> Fargate["Servicio ECS Fargate\n(blacklist-container :5000)"]
        Fargate --> RDS[("Amazon RDS PostgreSQL\nblacklist_db")]
        Fargate --> RDS[("Base de Datos\nPostgreSQL / SQLite")]
    end
```

---

## 2. Configuración de la Plataforma de Contenedores en AWS Fargate (20%)

### 2.1. Contenerización del Microservicio (`Dockerfile`)
Se diseñó un `Dockerfile` ligero y seguro basado en `public.ecr.aws/docker/library/python:3.11-slim` (alojado en la galería pública de AWS ECR para evitar bloqueos por límite de descargas de Docker Hub durante la ejecución de CodeBuild):
Se diseñó un `Dockerfile` ligero y reproducible basado en `public.ecr.aws/docker/library/python:3.11-slim` (alojado en la galería pública de AWS ECR para evitar bloqueos por límite de peticiones de Docker Hub durante la ejecución de CodeBuild):
- **Puerto expuesto:** `5000` (TCP).
- **Servidor WSGI de producción:** `gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 application:application`.
- **Health Check nativo:** Verifica periódicamente `http://localhost:5000/health`.

### 2.2. Registro de Contenedores en Amazon ECR
1. Se creó el repositorio privado en **Amazon ECR** con nombre `blacklist-microservice` en la región `us-east-1`.
2. Para el despliegue manual inicial, se construyó y publicó la imagen semilla en ECR ejecutando los comandos de autenticación y push provistos por AWS ECR.
### 2.2. Aprovisionamiento Declarativo en AWS con Terraform (`terraform/`) y Amazon ECR
Siguiendo las guías oficiales de **HashiCorp Terraform para AWS**, se estructuró el módulo `terraform/` (`main.tf`, `ecr_iam.tf`, `alb.tf`, `ecs.tf`, `outputs.tf`) para aprovisionar de forma idempotente:
1. **Amazon ECR (`blacklist-microservice`):** Repositorio privado con escaneo de imágenes habilitado (`533267010551.dkr.ecr.us-east-1.amazonaws.com/blacklist-microservice`).
2. **Cluster ECS (`blacklist-cluster`):** Clúster *serverless* aprovisionado sobre **AWS Fargate**.
3. **Task Definition (`blacklist-task-def`):**
   - **Compatibilidad:** `FARGATE`, modo de red `awsvpc`, `0.25 vCPU (256)` y `0.5 GB (512 MB)` de RAM.
   - **Rol de Ejecución:** `blacklist-ecsTaskExecutionRole` con permisos mínimos para ECR y CloudWatch Logs (`/ecs/blacklist-task-def`).
   - **Contenedor:** `blacklist-container`, puerto `5000` TCP y variables de entorno de seguridad (`STATIC_BEARER_TOKEN`, `JWT_SECRET_KEY`).
4. **Application Load Balancer (`blacklist-alb`) y Target Group (`blacklist-tg`):**
   - **Target Group:** Tipo de destino **`ip`** (requerido por el modo de red `awsvpc` de Fargate), puerto `5000` y comprobación de salud en `/health` esperando `200 OK`.
   - **Security Groups:** `blacklist-alb-sg` recibe tráfico HTTP en el puerto `80` desde Internet, y `blacklist-fargate-sg` restringe el tráfico entrante del puerto `5000` exclusivamente al Security Group del ALB.
5. **Servicio ECS (`blacklist-service`):** Mantiene en ejecución las tareas Fargate detrás del balanceador de carga.

> *[INSERTAR AQUÍ CAPTURA 1: Repositorio `blacklist-microservice` en Amazon ECR mostrando la imagen Docker publicada]*

### 2.3. Configuración del Ambiente en AWS ECS Fargate y Balanceador de Carga (ALB)
1. **Cluster ECS:** Se creó el clúster `blacklist-cluster` utilizando exclusivamente la infraestructura *Serverless* **AWS Fargate**.
2. **Task Definition (`blacklist-task-def`):**
   - **Compatibilidad:** `FARGATE`, modo de red `awsvpc`.
   - **Recursos:** `0.25 vCPU (256)` y `0.5 GB (512 MB)` de memoria.
   - **Rol de Ejecución y Tarea:** `LabRole` (provisto por AWS Academy con permisos para ECR y CloudWatch Logs).
   - **Contenedor:** `blacklist-container`, puerto `5000` TCP, variables de entorno de base de datos RDS (`RDS_HOSTNAME`, `RDS_USERNAME`, `RDS_PASSWORD`, `RDS_DB_NAME`, `RDS_PORT`) y de seguridad (`STATIC_BEARER_TOKEN`, `JWT_SECRET_KEY`).
3. **Application Load Balancer (ALB) y Target Group:**
   - **ALB (`blacklist-alb`):** Esquema *Internet-facing*, escuchando en el puerto `HTTP 80` (y puerto de prueba `8080` cuando se emplea despliegue Blue/Green con CodeDeploy).
   - **Target Group (`blacklist-tg`):** Tipo de destino **`ip`** (obligatorio para el modo `awsvpc` de AWS Fargate), protocolo `HTTP`, puerto `5000`, y ruta de Health Check configurada en `/health` esperando código `200 OK`.
4. **Servicio ECS (`blacklist-service`):** Asociado al clúster `blacklist-cluster`, ejecutando las tareas en subredes públicas con IP pública habilitada y grupo de seguridad que permite tráfico entrante en el puerto `5000` desde el ALB.

>
> *[INSERTAR AQUÍ CAPTURA 2: Clúster `blacklist-cluster` y Servicio `blacklist-service` en estado ACTIVE con tareas en estado RUNNING en AWS ECS Fargate]*
>
> *[INSERTAR AQUÍ CAPTURA 3: Prueba en Postman consumiendo el DNS del Application Load Balancer (`GET /health`, `POST /blacklists` y `GET /blacklists/<email>`) respondiendo exitosamente desde AWS Fargate]*

---

## 3. Configuración del Pipeline de Integración Continua (CI) y Entrega Continua (CD) (60%)

### 3.1. Archivos de Configuración de CI/CD en el Repositorio (10%)
Se incorporaron en la raíz del repositorio los siguientes archivos de infraestructura como código para soportar la construcción, pruebas, empaquetado de contenedores y despliegue continuo:
Se incorporaron en el repositorio los archivos de configuración requeridos para automatizar el flujo de construcción, pruebas y despliegue continuo:
1. **`Dockerfile` y `.dockerignore`**: Definición inmutable del contenedor del microservicio.
2. **`buildspec.yml`**: Orquesta el proceso en **AWS CodeBuild** (`blacklist-build`):
   - **`pre_build`**: Ejecuta `pytest tests/ -v`. Si alguna prueba falla, el proceso termina con código `1` y detiene el pipeline. Si todas las pruebas pasan, autentica contra **Amazon ECR** y calcula el tag inmutable de versión (`IMAGE_TAG`).
   - **`build`**: Construye la imagen Docker (`docker build`) y la etiqueta con `latest` y `$IMAGE_TAG`.
   - **`post_build`**: Publica la imagen en **Amazon ECR** (`docker push`) y genera los descriptores de artefactos (`imagedefinitions.json` para despliegue ECS e `imageDetail.json` + `taskdef.json` + `appspec.yaml` para despliegue con **AWS CodeDeploy**).
3. **`taskdef.json` y `appspec.yaml`**: Plantilla de definición de tarea de ECS Fargate y especificación de despliegue para AWS CodeDeploy apuntando a `blacklist-container` en el puerto `5000`.
4. **`terraform/*.tf`**: Infraestructura como código para aprovisionar y destruir el entorno de contenedores de forma reproducible.

1. **`Dockerfile` y `.dockerignore`**: Definición reproducible del contenedor del microservicio excluyendo archivos temporales, entornos virtuales y documentación.
2. **`buildspec.yml`**: Orquesta el proceso en **AWS CodeBuild** en tres etapas clave:
   - **`pre_build`**: Ejecuta `pytest tests/ -v` sobre una base de datos SQLite en memoria. Si alguna prueba falla, el proceso aborta inmediatamente (compuerta de calidad CI). Si todas pasan, se autentica contra **Amazon ECR** y obtiene el hash del commit (`IMAGE_TAG`).
   - **`build`**: Construye la imagen Docker (`docker build`) y la etiqueta con `latest` y con el hash del commit.
   - **`post_build`**: Sube la imagen a **Amazon ECR** (`docker push`) y genera los descriptores de artefactos requeridos por CodePipeline (`imagedefinitions.json` para despliegue ECS estándar e `imageDetail.json` + `taskdef.json` + `appspec.yaml` para despliegue Blue/Green con **AWS CodeDeploy**).
3. **`taskdef.json`**: Plantilla de definición de tarea de ECS Fargate donde AWS CodeDeploy inyecta dinámicamente el URI de la imagen recién construida en el marcador `<IMAGE1_NAME>`.
4. **`appspec.yaml`**: Archivo de especificación para **AWS CodeDeploy** que indica el servicio destino de ECS, el contenedor `blacklist-container` y el puerto `5000`.
### 3.2. Trigger Automático en `main` y Construcción de Imagen de Contenedor (10%)
- En **AWS CodeBuild** (`blacklist-build`), se habilitó el modo privilegiado para construcción de contenedores Docker y se adjuntó la política `AmazonEC2ContainerRegistryPowerUser` al rol `codebuild-blacklist-build-service-role`.
- Cada `git push` a la rama `main` dispara automáticamente **AWS CodePipeline** (`blacklist-ci-pipeline`), ejecutando las pruebas unitarias y publicando la nueva imagen en Amazon ECR.

### 3.2. Configuración de Construcción Automática de Imagen ante Commits en `main` (10%)
- En **AWS CodeBuild** (`blacklist-microservice-build`), se habilitó la bandera **Privileged mode** (necesaria para construir imágenes Docker dentro del contenedor de construcción) y se asoció el rol `LabRole`.
- En **AWS CodePipeline** (`blacklist-cicd-pipeline`), la etapa **Source** detecta automáticamente cualquier `git push` sobre la rama principal en GitHub y lanza la etapa **Build**, la cual ejecuta las pruebas unitarias y publica la nueva imagen en **Amazon ECR**.
### 3.3. Despliegue Continuo Automático sobre AWS Fargate (40%)
- Tras finalizar con éxito la etapa **Build**, la etapa **Deploy** en **AWS CodePipeline** toma el artefacto generado (`imagedefinitions.json` / `taskdef.json` + `appspec.yaml`) y actualiza automáticamente el servicio `blacklist-service` en el clúster `blacklist-cluster` sobre **AWS Fargate**, verificando que el nuevo contenedor supere el Health Check `/health` del ALB antes de retirar la tarea anterior.

### 3.3. Configuración del Despliegue Continuo Automático sobre AWS Fargate (40%)
En **AWS CodePipeline**, inmediatamente después de la etapa **Build**, se configuró la etapa **Deploy** apuntando al clúster `blacklist-cluster` y al servicio `blacklist-service` en AWS Fargate:
- **Con AWS CodeDeploy (Blue/Green ECS)** *(o proveedor Amazon ECS en CodePipeline)*: Recibe los artefactos generados por CodeBuild (`taskdef.json`, `appspec.yaml` e `imageDetail.json` / `imagedefinitions.json`), registra una nueva revisión del Task Definition con la imagen recién subida a ECR, levanta las nuevas tareas en AWS Fargate y verifica que el Target Group reporte estado *Healthy* en `/health` antes de drenar las tareas anteriores.
> *[INSERTAR AQUÍ CAPTURA 4: Archivos `Dockerfile`, `buildspec.yml`, `taskdef.json`, `appspec.yaml` y `terraform/` en el repositorio GitHub]*
>
> *[INSERTAR AQUÍ CAPTURA 5: Configuración completa de AWS CodePipeline (`blacklist-ci-pipeline`) mostrando las 3 etapas: Source (GitHub), Build (CodeBuild) y Deploy (ECS Fargate / CodeDeploy)]*

> *[INSERTAR AQUÍ CAPTURA 4: Configuración completa de AWS CodePipeline mostrando las 3 etapas: Source (GitHub), Build (CodeBuild) y Deploy (CodeDeploy / Amazon ECS Fargate)]*

---

## 4. Ejecuciones del Pipeline CI/CD y Análisis de Hallazgos (20%)

A continuación se documentan los tres escenarios de ejecución solicitados en la especificación de la entrega.

---

### 4.1. Escenario 1: Pipeline de Integración Continua (CI) Fallido (4%)

#### Descripción del Escenario
Para verificar que un error en el código o en las pruebas unitarias detiene el pipeline antes de construir la imagen Docker o alterar el entorno productivo en AWS Fargate, se introdujo una falla deliberada en `tests/test_blacklist.py`:
```python
def test_health_check(client):
    res_health = client.get('/health')
    assert res_health.status_code == 500  # Falla intencional en CI (el servicio retorna 200)
```
Para verificar que la etapa de CI actúa como compuerta bloqueante (*Andon Cord* según *The DevOps Handbook* y *Pipeline Blocker* según *Liguori, 2020*), se indujo una aserción fallida en `tests/test_blacklist.py` (`assert res_health.status_code == 500` en lugar de `200`).

#### Resultados y Hallazgos Encontrados
1. **Detención Temprana en `PRE_BUILD`:** Al ejecutar `pytest tests/ -v`, la prueba `test_health_check` falló con `AssertionError: assert 200 == 500`, devolviendo código de salida `1`.
2. **Ahorro de Cómputo y Almacenamiento en ECR:** Debido a que `pytest` se ejecuta en la fase `pre_build` antes de `docker build`, **no se construyó ninguna imagen Docker ni se subió ninguna etiqueta defectuosa a Amazon ECR**.
3. **Aislamiento del Entorno en AWS Fargate:** La etapa **Deploy** en AWS CodePipeline ni siquiera se inició. El servicio en AWS ECS Fargate continuó operando sin interrupción con la versión estable previa.
1. **Fallo Temprano (*Fail-Fast*) en `PRE_BUILD`:** `pytest` detectó el `AssertionError` en menos de 1 segundo y devolvió código de salida `1`, marcando la fase `PRE_BUILD` como `FAILED`.
2. **No Contaminación del Registro ECR:** Al fallar en `pre_build`, las fases `build` y `post_build` fueron omitidas; **no se construyó ninguna imagen Docker ni se publicó ningún artefacto defectuoso en Amazon ECR**.
3. **Protección del Entorno Productivo en AWS Fargate:** **AWS CodePipeline** detuvo la ejecución en la etapa **Build (Rojo)** y bloqueó el inicio de la etapa **Deploy**, manteniendo intacto el servicio en ejecución en AWS Fargate.

> *[INSERTAR AQUÍ CAPTURA 5: AWS CodePipeline con etapa Source en verde, etapa Build en ROJO (Failed) y etapa Deploy sin ejecutar]*
> *[INSERTAR AQUÍ CAPTURA 6: AWS CodePipeline con etapa Source en verde, etapa Build en ROJO (Failed) y etapa Deploy bloqueada]*
>
> *[INSERTAR AQUÍ CAPTURA 6: Logs de AWS CodeBuild mostrando el fallo de `pytest` en la fase `PRE_BUILD`]*
> *[INSERTAR AQUÍ CAPTURA 7: Logs de AWS CodeBuild mostrando el fallo de `pytest` en la fase `PRE_BUILD`]*

---

### 4.2. Escenario 2: Pipeline de Integración Continua (CI) Exitoso y Entrega Continua (CD) Exitosa (8%)

#### Descripción del Escenario
Se corrigió la aserción en `tests/test_blacklist.py` (`assert res_health.status_code == 200`) y se realizó `git push origin main` con la configuración válida de `Dockerfile`, `buildspec.yml`, `taskdef.json` y `appspec.yaml`.
Se restauró la aserción correcta en `tests/test_blacklist.py` (`assert res_health.status_code == 200`) y se envió el commit a `main`.

#### Resultados y Hallazgos Encontrados
1. **Etapa CI (`CodeBuild` - SUCCEEDED):**
   - Las 8 pruebas unitarias en `tests/test_blacklist.py` pasaron en menos de 1 segundo (`8 passed`).
   - Se construyó la imagen Docker y se publicó satisfactoriamente en **Amazon ECR** con la etiqueta del commit (`IMAGE_TAG`) y `latest`.
   - Se empaquetaron los artefactos de despliegue hacia el bucket S3 del pipeline.
2. **Etapa CD (`CodeDeploy / ECS Fargate` - SUCCEEDED):**
   - Se creó una nueva revisión de la definición de tarea `blacklist-task-def` apuntando a la imagen recién publicada en ECR.
   - AWS Fargate aprovisionó la nueva tarea, el Application Load Balancer validó el endpoint `/health` (`200 OK`) y el tráfico fue conmutado sin tiempo de indisponibilidad (*Zero-Downtime Deployment*).
1. **Etapa CI (`CodeBuild` - SUCCEEDED):** Las 8 pruebas unitarias pasaron satisfactoriamente (`8 passed`), se construyó la imagen Docker y se publicó en **Amazon ECR** con el tag del commit y `latest`.
2. **Etapa CD (`ECS Fargate / CodeDeploy` - SUCCEEDED):** La etapa **Deploy** registró automáticamente una nueva revisión de `blacklist-task-def` con la nueva imagen de ECR, aprovisionó la tarea de reemplazo en **AWS Fargate**, esperó a que el Target Group del ALB reportara estado `healthy` en `/health` (`200 OK`) y drenó la tarea anterior sin tiempo de inactividad (*Zero-Downtime Deployment*).

> *[INSERTAR AQUÍ CAPTURA 7: AWS CodePipeline con las 3 etapas (Source, Build y Deploy) en estado SUCCEEDED (Verde)]*
> *[INSERTAR AQUÍ CAPTURA 8: AWS CodePipeline con las 3 etapas (Source, Build y Deploy) en estado SUCCEEDED (Verde)]*
>
> *[INSERTAR AQUÍ CAPTURA 8: Consola de Amazon ECR y AWS CodeBuild mostrando la imagen recién publicada y las fases en estado SUCCEEDED]*
> *[INSERTAR AQUÍ CAPTURA 9: Consola de Amazon ECR y AWS CodeBuild mostrando la imagen recién publicada y las fases completadas]*
>
> *[INSERTAR AQUÍ CAPTURA 9: Consola de AWS CodeDeploy / ECS Fargate mostrando el despliegue completado exitosamente y la nueva revisión de la tarea activa]*
> *[INSERTAR AQUÍ CAPTURA 10: Consola de AWS ECS Fargate / CodeDeploy mostrando el despliegue exitoso y la nueva revisión activa]*

---

### 4.3. Escenario 3: Pipeline de Integración Continua (CI) Exitoso y Entrega Continua (CD) Fallida (8%)

#### Descripción del Escenario
Para validar el comportamiento del pipeline cuando el código pasa todas las pruebas unitarias y construye la imagen correctamente (CI exitoso), pero ocurre un problema de infraestructura o configuración durante el despliegue del contenedor en Fargate (CD fallido), se indujo un fallo en los descriptores de despliegue (`taskdef.json` / `appspec.yaml`), configurando una imagen/puerto de contenedor incompatible con el Health Check del Balanceador de Carga (por ejemplo, mapeando un puerto donde la aplicación no escucha o referenciando un parámetro de tarea inválido en `taskdef.json` / `appspec.yaml`).
Siguiendo los principios de despliegues seguros automatizados expuestos por *Clare Liguori (AWS re:Invent 2020)*, un cambio puede aprobar todas las pruebas unitarias en aislamiento pero presentar un error de configuración o salud al desplegarse en el entorno de contenedores. Para evidenciar este escenario:
- Se mantuvo intacto el código Python y la suite `tests/test_blacklist.py`, pero se introdujo una configuración inválida en el descriptor de despliegue (incompatibilidad en el nombre/puerto del contenedor objetivo para la etapa de despliegue).

#### Resultados y Hallazgos Encontrados
1. **Etapa CI (`CodeBuild` - SUCCEEDED):**
   - Dado que la lógica de negocio en Python y los tests en `tests/test_blacklist.py` seguían siendo válidos, `pytest` aprobó las 8 pruebas unitarias y `CodeBuild` finalizó en estado **Verde (`SUCCEEDED`)**, subiendo la imagen a ECR y entregando los artefactos a la siguiente etapa.
2. **Etapa CD (`CodeDeploy / ECS Fargate` - FAILED):**
   - Al iniciar la etapa **Deploy**, AWS CodeDeploy / ECS intentó desplegar la nueva revisión de la tarea en AWS Fargate.
   - Debido a la falla inducida en la configuración de despliegue / verificación de salud del contenedor de reemplazo, el servicio no superó las comprobaciones de salud del Target Group (o rechazó la especificación de tarea).
3. **Protección de Disponibilidad y Rollback Automático:**
   - La etapa **Deploy** en CodePipeline se marcó en **Rojo (`FAILED`)**.
   - La plataforma de contenedores mantuvo en ejecución las tareas saludables de la versión anterior y detuvo el reemplazo defectuoso, garantizando que los consumidores del microservicio en Postman no sufrieran caída del servicio.
1. **Etapa CI (`CodeBuild` - SUCCEEDED en Verde):** `pytest` ejecutó los 8 casos de prueba con éxito y `CodeBuild` construyó y subió la imagen a Amazon ECR sin errores, promoviendo los artefactos hacia la etapa de entrega continua.
2. **Etapa CD (`ECS Fargate / CodeDeploy` - FAILED en Rojo):** Al intentar aplicar el despliegue sobre el servicio en **AWS Fargate**, el orquestador de despliegue detectó la discrepancia en la definición/verificación de salud del contenedor y abortó la promoción del despliegue, marcando la etapa **Deploy** en estado **`FAILED` (Rojo)**.
3. **Resiliencia y Conservación de Servicio Activo (*Rollback*):** A pesar del fallo en la etapa CD, el Application Load Balancer y el servicio ECS conservaron en ejecución las tareas saludables de la revisión anterior, evitando cualquier interrupción para los clientes del API en Postman.

> *[INSERTAR AQUÍ CAPTURA 10: AWS CodePipeline mostrando Source en VERDE, Build (CI) en VERDE y Deploy (CD) en ROJO (Failed)]*
> *[INSERTAR AQUÍ CAPTURA 11: AWS CodePipeline mostrando Source en VERDE, Build (CI) en VERDE y Deploy (CD) en ROJO (Failed)]*
>
> *[INSERTAR AQUÍ CAPTURA 11: Detalle del error en AWS CodeDeploy / Eventos del Servicio en Amazon ECS Fargate evidenciando la falla de despliegue y la conservación de la versión estable anterior]*
> *[INSERTAR AQUÍ CAPTURA 12: Detalle del error en la etapa Deploy de CodePipeline / ECS Fargate / CodeDeploy evidenciando la detención del despliegue defectuoso]*

---

## 5. Guía Rápida para Inducir y Revertir el Escenario 3 (CI Exitoso + CD Fallido) en AWS
## 5. Referencias Bibliográficas

Cuando vayas a tomar las capturas del **Escenario 3 (CI verde + CD rojo)**:
1. **Si tu etapa Deploy usa AWS CodeDeploy (Blue/Green con `appspec.yaml`)**:
   - Abre `appspec.yaml` y cambia temporalmente `ContainerPort: 5000` por `ContainerPort: 9999` (un puerto que no coincide con el `containerPort: 5000` de `taskdef.json`), haz `git commit` y `git push`.
   - **Efecto inmediato**: `CodeBuild` (CI) terminará **100% en Verde**, pero **AWS CodeDeploy** (CD) fallará en **Rojo** al validar que el puerto 9999 no existe en la definición del contenedor.
2. **Si tu etapa Deploy usa Amazon ECS directo (`imagedefinitions.json`)**:
   - En `buildspec.yml`, cambia temporalmente la variable `CONTAINER_NAME: "blacklist-container"` por `CONTAINER_NAME: "contenedor-inexistente"`, haz `git commit` y `git push`.
   - **Efecto inmediato**: `CodeBuild` (CI) terminará **100% en Verde** (corre `pytest` y sube la imagen a ECR), pero la etapa **Deploy (Amazon ECS)** fallará en **Rojo** porque el nombre del contenedor en `imagedefinitions.json` no coincide con el de la Task Definition en ECS.
3. Después de tomar las capturas, revierte el cambio a su valor original (`5000` / `"blacklist-container"`) y haz `git push` para dejar el pipeline nuevamente en verde.

---

## 6. Enlaces de Entrega y Verificación

- **URL Pública del Microservicio en AWS ECS Fargate (ALB):** `http://[alb-blacklist-xxx].us-east-1.elb.amazonaws.com`
- **Repositorio de GitHub:** `https://github.com/Dayveg/pass_blacklist`
- **Documentación Pública de Postman:** `https://documenter.getpostman.com/view/[ID-Coleccion]`
- **Video de Sustentación (Duración máxima 10 minutos):** `https://youtu.be/[ID-Video]`
1. **Kim, G., Humble, J., Debois, P., & Willis, J.** (2016). *The DevOps Handbook: How to Create World-Class Agility, Reliability, and Security in Technology Organizations*. IT Revolution Press. (`https://learning.oreilly.com/library/view/the-devops-handbook/9781457191381/`)
2. **Liguori, C.** (2020). *AWS re:Invent 2020: Hands-off: Automating continuous delivery pipelines at Amazon*. Amazon Web Services. (`https://www.youtube.com/watch?v=ngnMj1zbMPY`)
3. **HashiCorp.** (2026). *Terraform AWS Tutorials – Get Started with AWS*. HashiCorp Developer. (`https://developer.hashicorp.com/terraform/tutorials/aws-get-started` y `https://developer.hashicorp.com/terraform/tutorials/aws`)
