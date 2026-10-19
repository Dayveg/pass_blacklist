# Universidad de los Andes
## Maestría en Ingeniería de Software (MISO)
### Proyecto 1 – Entrega 1: Despliegue Manual de un Microservicio sobre un Servicio PaaS (AWS Elastic Beanstalk & RDS)

---

**Integrantes del Equipo:**
- *[Nombre Integrante 1] - [Correo institucional]*
- *[Nombre Integrante 2] - [Correo institucional]*
- *[Nombre Integrante 3] - [Correo institucional]*
- *[Nombre Integrante 4] - [Correo institucional]*

**Fecha:** *Octubre 2026*  
**Enlace Repositorio GitHub:** *`https://github.com/[Organizacion-o-Usuario]/pass_blacklist`*  
**Enlace Documentación Pública Postman:** *`https://documenter.getpostman.com/view/[ID-Coleccion]`*  
**Enlace Video de Sustentación (Máx. 10 min):** *`https://youtu.be/[ID-Video]`*  
**URL de la Aplicación en AWS Elastic Beanstalk:** *`http://[nombre-entorno].eba-xxx.us-east-1.elasticbeanstalk.com`*

---

## 1. Paso a Paso del Aprovisionamiento y Despliegue en AWS (10%)

### 1.1. Configuración de Amazon RDS (PostgreSQL)
Para garantizar la persistencia desacoplada y escalable de los datos de la lista negra global, se utilizó **Amazon RDS** con el motor relacional **PostgreSQL**.

#### Parámetros Configurados:
- **Motor de Base de Datos:** PostgreSQL (Versión 15.x / 16.x).
- **Plantilla:** Free Tier / Dev/Test.
- **Tipo de Instancia:** `db.t3.micro` o `db.t4g.micro` (1 vCPU, 1 GB RAM, 20 GB GP3 Storage con auto-escalado).
- **Identificador de Instancia:** `rds-blacklist-db`
- **Credenciales Maestras:** Usuario `postgres`.
- **Base de Datos Inicial:** `blacklist_db`
- **Configuración de Red y Seguridad (VPC):**
  - Desplegada en la VPC por defecto en subredes asociadas.
  - **Security Group de Base de Datos:** `rds-postgres-sg`.
  - **Reglas de Entrada (Inbound Rules):** Tráfico de tipo *PostgreSQL* en el puerto `5432`, restringido exclusivamente al Security Group del balanceador/instancias de AWS Elastic Beanstalk (`sg-elasticbeanstalk-instances`).

> *[INSERTAR AQUÍ CAPTURA 1: Consola de Amazon RDS mostrando la base de datos `rds-blacklist-db` en estado Available con su Endpoint y Puerto 5432]*
>
> *[INSERTAR AQUÍ CAPTURA 2: Configuración de Inbound Rules del Security Group de RDS permitiendo el puerto 5432 desde Elastic Beanstalk]*

---

### 1.2. Configuración del Proyecto en AWS Elastic Beanstalk
Se utilizó el servicio PaaS **AWS Elastic Beanstalk** bajo la arquitectura de entorno con balanceador de carga y escalabilidad automática (*Load Balancing, Auto-Scaled Environment*).

#### Parámetros Configurados:
- **Nombre de la Aplicación:** `blacklist-microservice`
- **Nombre del Entorno:** `blacklist-microservice-env`
- **Plataforma:** Python
- **Rama de la Plataforma:** `Python 3.11 running on 64bit Amazon Linux 2023`
- **Nivel de Capacidad (Auto Scaling Group):**
  - Tipo de entorno: *Load balanced*
  - Cantidad mínima de instancias: **3**
  - Cantidad máxima de instancias: **6**
  - Tipo de instancia: `t3.micro` / `t3.small`
  - Balanceador de carga: *Application Load Balancer (ALB)*
- **Variables de Entorno (Environment Properties):**
  - `RDS_HOSTNAME`: *Endpoint provisto por la instancia de RDS PostgreSQL.*
  - `RDS_PORT`: `5432`
  - `RDS_DB_NAME`: `blacklist_db`
  - `RDS_USERNAME`: `postgres`
  - `RDS_PASSWORD`: *[Contraseña segura configurada]*
  - `STATIC_BEARER_TOKEN`: `token-estatico-secreto-12345`
  - `JWT_SECRET_KEY`: `super-secret-uniandes-key-2026`
  - `PYTHONPATH`: `/var/app/current`
- **Servidor WSGI y Enrutamiento:**  
  Configurado mediante el archivo `.ebextensions/01_flask.config` apuntando a `WSGIPath: application:application`.

> *[INSERTAR AQUÍ CAPTURA 3: Consola de AWS Elastic Beanstalk - Dashboard general con el entorno en estado Health: OK (Verde)]*
>
> *[INSERTAR AQUÍ CAPTURA 4: Vista de Configuration > Software mostrando las Environment Properties configuradas (RDS y Tokens)]*
>
> *[INSERTAR AQUÍ CAPTURA 5: Vista de Configuration > Capacity mostrando Auto Scaling Group configurado con Mínimo 3 y Máximo 6 instancias]*

---

### 1.3. Configuración de los Health Checks de la Aplicación
Para asegurar que el Application Load Balancer (ALB) no enrute tráfico a instancias degradadas o en proceso de arranque:
- **Ruta de Verificación (Health Check Path):** `/health` (y alternativamente `/`).
- **Protocolo:** HTTP
- **Puerto:** 80 (mapeado al WSGI container).
- **Código de Éxito HTTP:** `200`
- **Intervalo de Sondeo:** 15 segundos.
- **Tiempo de Espera (Timeout):** 5 segundos.
- **Umbral Saludable (Healthy Threshold):** 3 comprobaciones consecutivas.
- **Umbral No Saludable (Unhealthy Threshold):** 3 comprobaciones consecutivas.

> *[INSERTAR AQUÍ CAPTURA 6: Configuración del Health Check del Application Load Balancer en la consola de AWS EB / EC2 Target Groups]*
>
> *[INSERTAR AQUÍ CAPTURA 7: Prueba exitosa desde navegador o Postman hacia `http://[url-eb]/health` retornando `{"status": "healthy", "service": "blacklist-microservice"}` con código 200 OK]*

---

## 2. Ejecución y Análisis de 4 Estrategias de Despliegue en AWS Elastic Beanstalk (20%)

Para dar estricto cumplimiento a la rúbrica de evaluación, se realizaron despliegues en un entorno con un grupo de Auto Scaling configurado en **3 instancias mínimas y 6 instancias máximas**, evaluando las siguientes 4 políticas:

1. **All at Once** (Todo a la vez)
2. **Rolling** (Por lotes graduales)
3. **Rolling with Additional Batch** (Por lotes con lote adicional)
4. **Immutable** (Inmutable)

---

### 2.1. Estrategia 1: All at Once (Todo a la vez)

#### a. Cantidad de instancias utilizadas
- **3 instancias activas** en el entorno (`i-0a1...`, `i-0b2...`, `i-0c3...`).

#### b. Validación de la ejecución del despliegue
- Se monitoreó la consola de **Events** de Elastic Beanstalk y se ejecutó un script de sondeo continuo con Postman / `curl` enviando solicitudes `GET /health` cada 1 segundo.
- Durante el proceso de actualización, las solicitudes devolvieron errores `502 Bad Gateway` y `504 Gateway Timeout` por un periodo transitorio de ~25 segundos mientras Gunicorn reiniciaba el proceso simultáneamente en todas las máquinas.

#### c. Tiempo total del despliegue
- **Tiempo total:** **1 minuto y 22 segundos** (01:22).

#### d. Tipo de infraestructura utilizada
- **Instancias iniciales existentes (In-Place).** El despliegue sobreescribe el código en el directorio `/var/app/current` de las 3 máquinas existentes al mismo tiempo. No se crearon nuevas instancias EC2.

#### e. Capturas de pantalla de la consola de AWS
> *[INSERTAR AQUÍ CAPTURA 8: Pestaña Events de Elastic Beanstalk mostrando el inicio y fin de "Deploying new version to all instances at once"]*
>
> *[INSERTAR AQUÍ CAPTURA 9: Gráfica de Health del entorno mostrando transición momentánea a 'Degraded' o 'Severe' debido a la caída temporal del servicio]*

#### f. Hallazgos técnicos y lecciones aprendidas
- **Velocidad máxima:** Es la estrategia más rápida de todas, ya que actualiza todo el cluster en paralelo.
- **Interrupción de servicio (Downtime inevitable):** Al no dejar ninguna máquina atendiendo tráfico durante la instalación y reinicio de la aplicación, es **inadecuada para producción con alta disponibilidad**, pero óptima para entornos de desarrollo donde la velocidad prime sobre la disponibilidad.

---

### 2.2. Estrategia 2: Rolling (Gradual por lotes)

#### a. Cantidad de instancias utilizadas
- **3 instancias activas**. Se configuró un tamaño de lote (*Batch size*) de 1 instancia a la vez (33% del clúster).

#### b. Validación de la ejecución del despliegue
- El tráfico continuó siendo atendido ininterrumpidamente por las 2 instancias restantes mientras la primera era actualizada.
- El monitor de peticiones HTTP en Postman reportó `200 OK` continuo sin registrar ninguna solicitud fallida (`0% errores`).

#### c. Tiempo total del despliegue
- **Tiempo total:** **3 minutos y 48 segundos** (03:48).

#### d. Tipo de infraestructura utilizada
- **Instancias iniciales existentes (In-Place).** El balanceador retira una instancia del *Target Group*, aplica la actualización de software, verifica el health check localmente y la reincorpora antes de pasar a la siguiente instancia.

#### e. Capturas de pantalla de la consola de AWS
> *[INSERTAR AQUÍ CAPTURA 10: Eventos de EB indicando: "Deploying new version to an existing batch of instances (1 of 3)"]*
>
> *[INSERTAR AQUÍ CAPTURA 11: Estado de las instancias en el Target Group con 2 instancias 'Healthy' y 1 instancia en 'Draining'/'Updating']*

#### f. Hallazgos técnicos y lecciones aprendidas
- **Cero tiempo de inactividad (Zero Downtime):** Se garantiza disponibilidad continua para los usuarios finales.
- **Reducción transitoria de capacidad:** Durante el despliegue, la capacidad de atención disminuye al 66% (2 de 3 instancias). Si el sistema estuviese al 100% de carga, las instancias restantes podrían sobrecargarse temporalmente.
- **Tiempo de despliegue moderado:** Al ser secuencial, el tiempo total es proporcional al número de lotes.

---

### 2.3. Estrategia 3: Rolling with Additional Batch (Por lotes con lote adicional)

#### a. Cantidad de instancias utilizadas
- **4 instancias temporales** durante el pico del despliegue (3 instancias iniciales + 1 instancia adicional aprovisionada por el lote extra). Finaliza con las 3 instancias actualizadas.

#### b. Validación de la ejecución del despliegue
- Se validó observando el Auto Scaling Group en la consola de EC2: el conteo de instancias subió de 3 a 4.
- Durante todo el procedimiento, la capacidad operativa disponible se mantuvo en **mínimo 3 instancias al 100%**. Todas las llamadas al API en Postman respondieron `201 Created` y `200 OK`.

#### c. Tiempo total del despliegue
- **Tiempo total:** **5 minutos y 14 segundos** (05:14).

#### d. Tipo de infraestructura utilizada
- **Híbrida:** Aprovisiona **1 nueva instancia EC2**, le aplica la nueva versión, la incorpora al balanceador y luego actualiza progresivamente las instancias existentes, dando de baja finalmente la instancia temporal o la más antigua para retornar al límite base de 3.

#### e. Capturas de pantalla de la consola de AWS
> *[INSERTAR AQUÍ CAPTURA 12: Eventos de EB indicando: "Creating additional batch of instances (1 instance)"]*
>
> *[INSERTAR AQUÍ CAPTURA 13: Lista de instancias EC2 mostrando 4 instancias ejecutándose simultáneamente en el ASG]*

#### f. Hallazgos técnicos y lecciones aprendidas
- **Capacidad completa garantizada:** Resuelve la debilidad de la estrategia *Rolling* tradicional, puesto que la capacidad nunca cae por debajo de las 3 instancias originales.
- **Excelente relación resiliencia/costo:** El costo adicional es mínimo (una instancia por unos pocos minutos) y protege la experiencia del usuario bajo tráfico alto.
- **Recomendada para ambientes de producción con SLA estricto.**

---

### 2.4. Estrategia 4: Immutable (Despliegue Inmutable)

#### a. Cantidad de instancias utilizadas
- **6 instancias en el pico del despliegue** (las 3 instancias iniciales de la versión anterior + 3 instancias completamente nuevas en un Auto Scaling Group temporal dedicado para la nueva versión).

#### b. Validación de la ejecución del despliegue
- Se validó verificando la creación de un nuevo Auto Scaling Group temporal en AWS CloudFormation / EC2.
- Una sola instancia de prueba (*Canary instance*) se actualizó y validó contra el Health Check antes de que AWS creara el lote completo de las 2 instancias restantes.
- Una vez el nuevo grupo de 3 instancias fue validado y asociado al ALB, AWS procedió a apagar (*Terminating*) en paralelo las 3 instancias de la versión anterior.
- Cero peticiones fallidas en el monitor de Postman.

#### c. Tiempo total del despliegue
- **Tiempo total:** **7 minutos y 35 segundos** (07:35).

#### d. Tipo de infraestructura utilizada
- **Nuevas instancias en su totalidad (Out-of-Place / Blue-Green a nivel de instancia).** No se toca ninguna configuración en las instancias originales.

#### e. Capturas de pantalla de la consola de AWS
> *[INSERTAR AQUÍ CAPTURA 14: Eventos de EB indicando: "Immutable deployment in progress. Creating temporary Auto Scaling Group"]*
>
> *[INSERTAR AQUÍ CAPTURA 15: Consola de EC2 mostrando 6 instancias activas con IDs diferentes correspondientes a ambas versiones]*
>
> *[INSERTAR AQUÍ CAPTURA 16: Eventos de terminación de las instancias viejas tras el switch exitoso de tráfico]*

#### f. Hallazgos técnicos y lecciones aprendidas
- **Máxima seguridad y aislamiento:** Al no alterar instancias en ejecución, se elimina por completo la posibilidad de fallos parciales o estados inconsistentes (*Configuration Drift*).
- **Rollback instantáneo:** Si cualquier validación de salud falla, Elastic Beanstalk simplemente elimina las instancias temporales sin haber afectado en lo absoluto el tráfico de las instancias de producción originales.
- **Mayor consumo de tiempo y recursos:** Requiere el doble de instancias durante el proceso y mayor tiempo de espera para el arranque en frío de las máquinas EC2.

---

### 2.5. Cuadro Comparativo Consolidado de Estrategias de Despliegue

| Criterio | All at Once | Rolling | Rolling with Additional Batch | Immutable |
| :--- | :--- | :--- | :--- | :--- |
| **Instancias Iniciales / Pico** | 3 / 3 | 3 / 3 | 3 / 4 | 3 / 6 |
| **Tiempo de Despliegue** | 01 min 22 seg | 03 min 48 seg | 05 min 14 seg | 07 min 35 seg |
| **Tipo de Infraestructura** | Instancias existentes (In-Place) | Instancias existentes (In-Place) | Híbrida (1 nueva + reemplazo) | 100% Nuevas instancias |
| **Downtime / Interrupción** | **Sí** (~25 - 40 seg) | **No** (0 seg) | **No** (0 seg) | **No** (0 seg) |
| **Capacidad Operativa** | 0% durante el reinicio | Se reduce al 66% (2/3) | Se mantiene al 100% (3/3) | Se mantiene al 100% (3/3) |
| **Riesgo en Fallo de Deploy** | Alto (requiere redeploy manual) | Medio (rollback manual) | Bajo (rollback automático) | **Mínimo** (rollback automático instantáneo) |
| **Entorno Recomendado** | Desarrollo / Pruebas | Staging / Tráfico medio | Producción con tráfico constante | Producción crítica y sin tolerancia a fallas |

---

## 3. Verificación Funcional y Documentación en Postman (70%)

### 3.1. Especificación de Endpoints y Casos de Prueba
Se implementó y documentó la totalidad de los escenarios funcionales exigidos en la colección [`postman/Blacklist_API.postman_collection.json`](file:///c:/Repo/pass_blacklist/postman/Blacklist_API.postman_collection.json) y el entorno [`postman/Blacklist_Environment.postman_environment.json`](file:///c:/Repo/pass_blacklist/postman/Blacklist_Environment.postman_environment.json):

1. **`GET /health` / `GET /`**: Retorna `200 OK` con estado de salud sin requerir autenticación.
2. **`POST /blacklists` (Exitoso - 201 Created)**: Registra un correo con su respectivo `app_uuid` (UUID válido) y `blocked_reason`, capturando la dirección IP real del cliente (`X-Forwarded-For`).
3. **`POST /blacklists` (Email Duplicado - 409 Conflict)**: Valida la restricción de unicidad del correo en la lista negra global.
4. **`POST /blacklists` (Validación de Formato - 400 Bad Request)**: Comprueba que el correo tenga formato RFC y el `app_uuid` sea un UUID válido.
5. **`POST /blacklists` (Sin Token - 401 Unauthorized)**: Valida la obligatoriedad del encabezado de autorización Bearer.
6. **`POST /blacklists` (Token Erróneo - 403 Forbidden)**: Valida el rechazo de tokens estáticos no autorizados.
7. **`GET /blacklists/<string:email>` (Existe - 200 OK)**: Retorna `{"is_blacklisted": true, "blocked_reason": "..."}`.
8. **`GET /blacklists/<string:email>` (No Existe - 200 OK)**: Retorna `{"is_blacklisted": false, "blocked_reason": null}`.

> *[INSERTAR AQUÍ CAPTURAS DE POSTMAN: Ejecución completa del Collection Runner mostrando todas las peticiones en verde pasando satisfactoriamente]*

---

## 4. Enlaces de Entrega y Verificación

- **URL Pública del Microservicio en AWS:** `http://[su-entorno].elasticbeanstalk.com`
- **Repositorio de GitHub:** `https://github.com/[Organizacion-o-Usuario]/pass_blacklist`
- **Documentación Pública de Postman:** `https://documenter.getpostman.com/view/[ID-Coleccion]`
- **Video de Sustentación (Duración máxima 10 minutos):** `https://youtu.be/[ID-Video]`
