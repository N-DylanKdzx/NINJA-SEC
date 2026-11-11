# NINJA-SEC · Checklist Técnico de Avance del Centro de Datos Multicloud

> **Documento de Contexto y Control de Tareas Técnicas**  
> **Fuente:** `NINJA-SEC_Avance_Tecnico.xlsx`  
> **Hoja de Ruta y Dependencias:** Consulta [`FLUJO_DE_TRABAJO_Y_DESBLOQUEO.md`](FLUJO_DE_TRABAJO_Y_DESBLOQUEO.md) para conocer la secuencia de ejecución nivel por nivel y los criterios de desbloqueo.  

## 1. Guía de Uso del Checklist

Este documento refleja el checklist técnico del proyecto NINJA-SEC estructurado a partir del archivo Excel maestro. Se ha preparado como un checklist de seguimiento donde todas las tareas inician en estado **Pendiente** o **Bloqueado** (tareas dependientes de componentes aplazados como AWS), disponiendo de un apartado específico al costado de cada tarea para consignar su **justificación y sustento de evidencia** a medida que pasen a estado completado.

### Convenciones de Estado
- `[ ] Pendiente`: Tarea planificada lista para ejecución técnica.
- `[-] Bloqueado`: Tarea bloqueada o aplazada por decisión del proyecto (ej. entorno AWS).
- `[x] Completado`: Tarea ejecutada y verificada (al marcar, consignar la evidencia en el apartado correspondiente).

### Registro de Justificación y Evidencia (Uso Futuro)
La columna **`Justificación / Sustento de Evidencia`** se encuentra inicialmente vacía y lista para documentar el respaldo técnico cuando una tarea se complete:
- **Identificador del recurso:** OCID, Resource ID de Azure, ARN o endpoint.
- **Comando ejecutado / Verificación:** Comando CLI (`oci`, `az`, `terraform`, etc.) y salida de validación.
- **Ruta o prueba:** Archivo de salida, log o prueba de aceptación.

### Referencia de Pilares
| Pilar | Descripción |
| :---: | :--- |
| **P1** | Conectividad e Interconexión |
| **P2** | Base de Datos y Replicación |
| **P3a** | Seguridad Perimetral y WAF |
| **P3b** | Resiliencia y Alta Disponibilidad |
| **P3c** | Auditoría y Almacenamiento Inmutable |
| **P4** | Observabilidad y Monitoreo |
| **P5** | Infraestructura como Código (IaC) |
| **—** | Base y Preparación |

## 2. Resumen Ejecutivo por Dominio

| Cód | Dominio Técnico | Total Tareas | Núcleo | Secundario | Pendientes `[ ]` | Bloqueadas `[-]` | Completadas `[x]` |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **[G](#dominio-g---preparación-de-cuentas-y-herramientas)** | Preparación de cuentas y herramientas | 19 | 18 | 1 | 8 | 5 | 6 |
| **[A](#dominio-a---aws-us-east-1-vpc-10100016)** | AWS · us-east-1 (VPC 10.10.0.0/16) | 95 | 88 | 7 | 0 | 95 | 0 |
| **[B](#dominio-b---oci-home-region-vcn-10200016)** | OCI · Home Region (VCN 10.20.0.0/16) | 61 | 56 | 5 | 0 | 10 | 51 |
| **[C](#dominio-c---azure-east-us-cumplimiento-y-forense)** | Azure · East US (cumplimiento y forense) | 17 | 16 | 1 | 12 | -2 | 11 |
| **[D](#dominio-d---cloudflare-dns-y-borde)** | Cloudflare · DNS y borde | 7 | 6 | 1 | 2 | 5 | 0 |
| **[M](#dominio-m---integraciones-multicloud)** | Integraciones Multicloud | 55 | 53 | 2 | 6 | 49 | 0 |
| **[T](#dominio-t---seguridad-transversal)** | Seguridad transversal | 20 | 19 | 1 | 5 | 15 | 0 |
| **[R](#dominio-r---continuidad-backup-y-dr)** | Continuidad: Backup y DR | 8 | 8 | 0 | 0 | 8 | 0 |
| **[P](#dominio-p---ensayo-técnico-de-sustentación)** | Ensayo técnico de sustentación | 13 | 13 | 0 | 2 | 11 | 0 |
| **[K](#dominio-k---operación-y-control-de-costos)** | Operación y control de costos | 8 | 8 | 0 | 0 | 8 | 0 |
| **TOTAL** | **Consolidado General** | **303** | **285** | **18** | **35** | **200** | **68** |

### Índice de Dominios
- [Dominio G: Preparación de cuentas y herramientas](#dominio-g---preparación-de-cuentas-y-herramientas) (19 tareas)
- [Dominio A: AWS · us-east-1 (VPC 10.10.0.0/16)](#dominio-a---aws-us-east-1-vpc-10100016) (95 tareas)
- [Dominio B: OCI · Home Region (VCN 10.20.0.0/16)](#dominio-b---oci-home-region-vcn-10200016) (61 tareas)
- [Dominio C: Azure · East US (cumplimiento y forense)](#dominio-c---azure-east-us-cumplimiento-y-forense) (17 tareas)
- [Dominio D: Cloudflare · DNS y borde](#dominio-d---cloudflare-dns-y-borde) (7 tareas)
- [Dominio M: Integraciones Multicloud](#dominio-m---integraciones-multicloud) (55 tareas)
- [Dominio T: Seguridad transversal](#dominio-t---seguridad-transversal) (20 tareas)
- [Dominio R: Continuidad: Backup y DR](#dominio-r---continuidad-backup-y-dr) (8 tareas)
- [Dominio P: Ensayo técnico de sustentación](#dominio-p---ensayo-técnico-de-sustentación) (13 tareas)
- [Dominio K: Operación y control de costos](#dominio-k---operación-y-control-de-costos) (8 tareas)

---

## 3. Checklist Técnico Detallado

<a id="dominio-g---preparación-de-cuentas-y-herramientas"></a>

## Dominio G: Preparación de cuentas y herramientas

<a id="comp-g1"></a>

### Componente G1: Cuentas y accesos
- **Fase:** F0 | **Pilar:** — | **Total Tareas:** 7

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **G1.1** | `[-] Bloqueado` | AWS Academy Learner Lab iniciado (lab activo en us-east-1) | — | F0 | — | Núcleo |  |
| **G1.2** | `[x] Completado` | Cuenta OCI creada con home region elegida | — | F0 | — | Núcleo |OCI CLI: iam region-subscription list confirmó us-ashburn-1 como región principal; os ns get respondió correctamente. |
| **G1.3** | `[x] Completado` | OCI Free Trial activado (US$300 / 30 días) si hay tarjeta disponible | Opcional: solo si se quiere probar OCI WAF u otros servicios de pago | F0 | — | Secundario | OCI Organizations ListAssignedSubscriptions confirmó una suscripción CLOUDCM ACTIVE con vigencia de 30 días, del 2026-11-05 al 2026-12-04 UTC. El titular confirmó que corresponde al Free Trial activado al abrir la cuenta. La API consultada no muestra el saldo de créditos restante. |
| **G1.4** | `[x] Completado` | Azure for Students activado (sin tarjeta) | — | F0 | — | Núcleo | az account show confirma Azure for Students, Enabled, suscripción 020556eb-782f-4afc-84d3-39cd392763ba. |
| **G1.5** | `[ ] Pendiente` | Cuenta Cloudflare Free creada | — | F0 | — | Núcleo |  |
| **G1.6** | `[ ] Pendiente` | Dominio real registrado y delegado a Cloudflare | Cloudflare requiere un dominio que controles; un subdominio de nip.io no se puede delegar | F0 | — | Núcleo |  |
| **G1.7** | `[-] Bloqueado` | Llaves SSH generadas (key pair AWS + llave OCI) | — | F0 | — | Núcleo |  |


<a id="comp-g2"></a>

### Componente G2: Herramientas locales y repositorio
- **Fase:** F0 | **Pilar:** P5 | **Total Tareas:** 6

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **G2.1** | `[ ] Pendiente` | Terraform instalado (terraform --version responde) | — | F0 | P5 | Núcleo |  |
| **G2.2** | `[-] Bloqueado` | AWS CLI configurado con credenciales del Lab | — | F0 | P5 | Núcleo |  |
| **G2.3** | `[ ] Pendiente` | OCI CLI configurado con API key | — | F0 | P5 | Núcleo |  |
| **G2.4** | `[x] Completado` | Azure CLI autenticado (az login) | — | F0 | P5 | Núcleo | Inicio de sesión completado; az account show y az resource list devolvieron la suscripción y sus recursos. |
| **G2.5** | `[ ] Pendiente` | Repositorio Git creado con estructura terraform/ (environments/prod + modules) | — | F0 | P5 | Núcleo |  |
| **G2.6** | `[ ] Pendiente` | .gitignore protege terraform.tfvars, llaves y credenciales | — | F0 | P5 | Núcleo |  |


<a id="comp-g3"></a>

### Componente G3: Verificación de servicios disponibles (decide Plan A / Plan B)
- **Fase:** F0 | **Pilar:** — | **Total Tareas:** 6

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **G3.1** | `[-] Bloqueado` | VPN Connection / Virtual Private Gateway disponible en Academy | Si ❌ → Plan B: WireGuard en EC2 | F0 | — | Núcleo |  |
| **G3.2** | `[-] Bloqueado` | Route 53 verificado (disponible o descartado → Cloudflare primario) | — | F0 | — | Núcleo |  |
| **G3.3** | `[-] Bloqueado` | AWS WAF verificado (disponible o descartado → ModSecurity primario) | — | F0 | — | Núcleo |  |
| **G3.4** | `[-] Bloqueado` | binlog_format=ROW configurable en RDS vía parameter group | Si ❌ → dual-write como mecanismo principal | F0 | — | Núcleo |  |
| **G3.5** | `[x] Completado` | Capacidad A1 Flex confirmada en OCI (o decidido fallback 2×E2.1.Micro) | — | F0 | — | Núcleo | OCI LaunchInstance devolvió Out of host capacity para VM.Standard.A1.Flex en AD-1, AD-2 y AD-3. Se adoptó la alternativa de dos E2.1.Micro verificada en B2.4. |
| **G3.6** | `[x] Completado` | Capacidad MySQL HeatWave Always Free confirmada | — | F0 | — | Núcleo | OCI Limits confirmó mysql-free-count=1 en AD-3. GetDbSystem y SELECT VERSION() confirmaron MySQL.Free activo y operativo en Ashburn. |


---

<a id="dominio-a---aws-us-east-1-vpc-10100016"></a>

## Dominio A: AWS · us-east-1 (VPC 10.10.0.0/16)

<a id="comp-a1"></a>

### Componente A1: Red VPC y segmentación
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 11

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A1.1** | `[-] Bloqueado` | VPC 10.10.0.0/16 creada | — | F1 | — | Núcleo |  |
| **A1.2** | `[-] Bloqueado` | Subred pública Web-01 10.10.1.0/24 (AZ-1a) | — | F1 | — | Núcleo |  |
| **A1.3** | `[-] Bloqueado` | Subred pública Web-02 10.10.2.0/24 (AZ-1b) | — | F1 | — | Núcleo |  |
| **A1.4** | `[-] Bloqueado` | Subred privada APP 10.10.10.0/24 (AZ-1a) | — | F1 | — | Núcleo |  |
| **A1.5** | `[-] Bloqueado` | Subred privada BD 10.10.20.0/24 (AZ-1a) | — | F1 | — | Núcleo |  |
| **A1.6** | `[-] Bloqueado` | Subred privada BD secundaria 10.10.21.0/24 (AZ-1b) | RDS exige un DB Subnet Group con subredes en al menos 2 AZ | F1 | — | Núcleo |  |
| **A1.7** | `[-] Bloqueado` | Internet Gateway creado y adjunto a la VPC | — | F1 | — | Núcleo |  |
| **A1.8** | `[-] Bloqueado` | Route Table pública (0.0.0.0/0 → IGW) asociada a subredes públicas | — | F1 | — | Núcleo |  |
| **A1.9** | `[-] Bloqueado` | Route Table privada (0.0.0.0/0 → NAT Instance) asociada a subredes privadas | — | F1 | — | Núcleo |  |
| **A1.10** | `[-] Bloqueado` | NACLs por capa configuradas | — | F1 | — | Secundario |  |
| **A1.11** | `[-] Bloqueado` | VPC Flow Logs hacia CloudWatch Logs | — | F1 | — | Secundario |  |


<a id="comp-a2"></a>

### Componente A2: NAT Instance (salida de subredes privadas)
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A2.1** | `[-] Bloqueado` | EC2 t2.nano lanzada en subred pública con Elastic IP | — | F1 | — | Núcleo |  |
| **A2.2** | `[-] Bloqueado` | Source/Dest check deshabilitado | — | F1 | — | Núcleo |  |
| **A2.3** | `[-] Bloqueado` | iptables MASQUERADE + net.ipv4.ip_forward persistentes tras reinicio | — | F1 | — | Núcleo |  |
| **A2.4** | `[-] Bloqueado` | Instancia privada sale a Internet por la NAT (traceroute/curl verificado) | — | F1 | — | Núcleo |  |


<a id="comp-a3"></a>

### Componente A3: Security Groups por capa
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 7

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A3.1** | `[-] Bloqueado` | alb-sg: 80/443 desde 0.0.0.0/0 (única regla abierta al mundo) | — | F1 | — | Núcleo |  |
| **A3.2** | `[-] Bloqueado` | web-sg: 80/443 solo desde alb-sg | — | F1 | — | Núcleo |  |
| **A3.3** | `[-] Bloqueado` | app-sg: 8080 solo desde web-sg | — | F1 | — | Núcleo |  |
| **A3.4** | `[-] Bloqueado` | db-sg: 3306 solo desde app-sg | — | F1 | — | Núcleo |  |
| **A3.5** | `[-] Bloqueado` | nat-sg: tráfico solo desde subredes privadas | — | F1 | — | Núcleo |  |
| **A3.6** | `[-] Bloqueado` | SSH sin 0.0.0.0/0 (acceso restringido a origen conocido) | — | F1 | — | Núcleo |  |
| **A3.7** | `[-] Bloqueado` | Revisión final: ninguna regla 0.0.0.0/0 salvo alb-sg | — | F1 | — | Núcleo |  |


<a id="comp-a4"></a>

### Componente A4: Cómputo: capa web (web-01 / web-02)
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 8

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A4.1** | `[-] Bloqueado` | Launch Template de web tier creado (AMI, t2.micro, SG, User Data) | — | F1 | — | Núcleo |  |
| **A4.2** | `[-] Bloqueado` | web-01 t2.micro en AZ-1a operativo | — | F1 | — | Núcleo |  |
| **A4.3** | `[-] Bloqueado` | web-02 t2.micro en AZ-1b operativo | — | F1 | — | Núcleo |  |
| **A4.4** | `[-] Bloqueado` | Nginx instalado y sirviendo el frontend del portal | — | F1 | — | Núcleo |  |
| **A4.5** | `[-] Bloqueado` | Frontend del portal NINJA-SEC desplegado | — | F1 | — | Núcleo |  |
| **A4.6** | `[-] Bloqueado` | Proxy inverso /api → app-backend:8080 funcionando | — | F1 | — | Núcleo |  |
| **A4.7** | `[-] Bloqueado` | User Data: servicios arrancan solos al reiniciar la instancia | — | F1 | — | Núcleo |  |
| **A4.8** | `[-] Bloqueado` | Volúmenes EBS cifrados | — | F1 | — | Núcleo |  |


<a id="comp-a5"></a>

### Componente A5: WAF nginx + ModSecurity (OWASP CRS)
- **Fase:** F1 | **Pilar:** P3a | **Total Tareas:** 9

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A5.1** | `[-] Bloqueado` | ModSecurity v3 + conector nginx instalados | — | F1 | P3a | Núcleo |  |
| **A5.2** | `[-] Bloqueado` | OWASP Core Rule Set instalado y cargado | — | F1 | P3a | Núcleo |  |
| **A5.3** | `[-] Bloqueado` | Motor en modo bloqueo (SecRuleEngine On, no DetectionOnly) | — | F1 | P3a | Núcleo |  |
| **A5.4** | `[-] Bloqueado` | Mismo WAF activo en web-01 y web-02 | — | F1 | P3a | Núcleo |  |
| **A5.5** | `[-] Bloqueado` | Payload SQLi → HTTP 403 (regla 942xxx en log) | — | F1 | P3a | Núcleo |  |
| **A5.6** | `[-] Bloqueado` | Payload XSS → HTTP 403 | — | F1 | P3a | Núcleo |  |
| **A5.7** | `[-] Bloqueado` | Log de ModSecurity enviado a CloudWatch Logs (/ninjasec/waf/blocked) | — | F1 | P3a | Núcleo |  |
| **A5.8** | `[-] Bloqueado` | Metric filter + alarma sobre bloqueos WAF | — | F1 | P3a | Secundario |  |
| **A5.9** | `[-] Bloqueado` | AWS WAF delante del ALB (solo si Academy lo permite) | — | F1 | P3a | Secundario |  |


<a id="comp-a6"></a>

### Componente A6: Backend: API Flask y portal de incidentes
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 8

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A6.1** | `[-] Bloqueado` | EC2 app-backend t2.micro en subred privada APP | — | F1 | — | Núcleo |  |
| **A6.2** | `[-] Bloqueado` | API REST Flask con CRUD de incidentes | — | F1 | — | Núcleo |  |
| **A6.3** | `[-] Bloqueado` | Servicio systemd con arranque automático | — | F1 | — | Núcleo |  |
| **A6.4** | `[-] Bloqueado` | Endpoint /health respondiendo | — | F1 | — | Núcleo |  |
| **A6.5** | `[-] Bloqueado` | Acceso al backend solo desde web-sg (verificado) | — | F1 | — | Núcleo |  |
| **A6.6** | `[-] Bloqueado` | Credenciales leídas desde Secrets Manager (sin texto plano) | — | F1 | — | Núcleo |  |
| **A6.7** | `[-] Bloqueado` | Portal: crear / leer / actualizar / eliminar incidente funciona de extremo a extremo | — | F1 | — | Núcleo |  |
| **A6.8** | `[-] Bloqueado` | Logs de aplicación enviados a CloudWatch Logs | — | F1 | — | Secundario |  |


<a id="comp-a7"></a>

### Componente A7: Application Load Balancer + HTTPS
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 7

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A7.1** | `[-] Bloqueado` | ALB creado en las 2 subredes públicas | — | F1 | — | Núcleo |  |
| **A7.2** | `[-] Bloqueado` | Target Group web con health check configurado | — | F1 | — | Núcleo |  |
| **A7.3** | `[-] Bloqueado` | web-01 y web-02 registrados como targets saludables | — | F1 | — | Núcleo |  |
| **A7.4** | `[-] Bloqueado` | Listener HTTPS 443 con certificado (ACM o autofirmado) | — | F1 | — | Núcleo |  |
| **A7.5** | `[-] Bloqueado` | Listener HTTP 80 redirige a HTTPS | — | F1 | — | Núcleo |  |
| **A7.6** | `[-] Bloqueado` | Balanceo verificado (tráfico llega a ambas instancias) | — | F1 | — | Núcleo |  |
| **A7.7** | `[-] Bloqueado` | Falla simulada de web-01 → servicio continúa por web-02 | — | F1 | — | Núcleo |  |


<a id="comp-a8"></a>

### Componente A8: Auto Scaling Group (web tier)
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A8.1** | `[-] Bloqueado` | ASG creado: mín 2 / máx 4, repartido en 2 AZ | — | F1 | — | Núcleo |  |
| **A8.2** | `[-] Bloqueado` | ASG asociado al Target Group del ALB | — | F1 | — | Núcleo |  |
| **A8.3** | `[-] Bloqueado` | Política de escalado por CPU configurada | — | F1 | — | Núcleo |  |
| **A8.4** | `[-] Bloqueado` | Prueba de carga dispara una instancia nueva | — | F1 | — | Núcleo |  |
| **A8.5** | `[-] Bloqueado` | Instancia terminada manualmente es reemplazada | — | F1 | — | Núcleo |  |


<a id="comp-a9"></a>

### Componente A9: RDS MySQL (BD primaria)
- **Fase:** F1 | **Pilar:** P2 | **Total Tareas:** 8

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A9.1** | `[-] Bloqueado` | DB Subnet Group con subredes privadas de 2 AZ | — | F1 | P2 | Núcleo |  |
| **A9.2** | `[-] Bloqueado` | RDS MySQL db.t2.micro desplegado en subred privada | — | F1 | P2 | Núcleo |  |
| **A9.3** | `[-] Bloqueado` | Publicly accessible = No | — | F1 | P2 | Núcleo |  |
| **A9.4** | `[-] Bloqueado` | Cifrado en reposo habilitado | — | F1 | P2 | Núcleo |  |
| **A9.5** | `[-] Bloqueado` | Backups automáticos con retención de 7 días | — | F1 | P2 | Núcleo |  |
| **A9.6** | `[-] Bloqueado` | Parameter group con binlog_format=ROW aplicado | — | F1 | P2 | Núcleo |  |
| **A9.7** | `[-] Bloqueado` | Esquema de NINJA-SEC (tabla incidents) y usuario de aplicación creados | — | F1 | P2 | Núcleo |  |
| **A9.8** | `[-] Bloqueado` | Conexión solo desde app-backend (intento desde Internet rechazado) | — | F1 | P2 | Núcleo |  |


<a id="comp-a10"></a>

### Componente A10: KMS y Secrets Manager
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 6

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A10.1** | `[-] Bloqueado` | Clave KMS propia creada | — | F1 | — | Núcleo |  |
| **A10.2** | `[-] Bloqueado` | Secreto: credenciales de RDS | — | F1 | — | Núcleo |  |
| **A10.3** | `[-] Bloqueado` | Secreto: endpoint/credenciales de MySQL HeatWave (OCI) | — | F1 | — | Núcleo |  |
| **A10.4** | `[-] Bloqueado` | Secreto: SAS token de Azure Blob | — | F1 | — | Núcleo |  |
| **A10.5** | `[-] Bloqueado` | Backend obtiene secretos por ARN (get-secret-value funciona) | — | F1 | — | Núcleo |  |
| **A10.6** | `[-] Bloqueado` | Política de recurso limita quién lee cada secreto | — | F1 | — | Núcleo |  |


<a id="comp-a11"></a>

### Componente A11: S3 y estado remoto
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 8

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A11.1** | `[-] Bloqueado` | Bucket de assets estáticos | — | F1 | — | Núcleo |  |
| **A11.2** | `[-] Bloqueado` | Bucket de auditoría (ninjasec-audit) para CloudTrail | — | F1 | — | Núcleo |  |
| **A11.3** | `[-] Bloqueado` | Versionado habilitado | — | F1 | — | Núcleo |  |
| **A11.4** | `[-] Bloqueado` | Lifecycle policy configurada | — | F1 | — | Núcleo |  |
| **A11.5** | `[-] Bloqueado` | Cifrado SSE-KMS en buckets | — | F1 | — | Núcleo |  |
| **A11.6** | `[-] Bloqueado` | Block Public Access activo | — | F1 | — | Núcleo |  |
| **A11.7** | `[-] Bloqueado` | Bucket de estado Terraform (ninjasec-terraform-state) | — | F1 | — | Núcleo |  |
| **A11.8** | `[-] Bloqueado` | Tabla DynamoDB de lock (ninjasec-tfstate-lock) | — | F1 | — | Núcleo |  |


<a id="comp-a12"></a>

### Componente A12: CloudTrail (auditoría)
- **Fase:** F1 | **Pilar:** P3c | **Total Tareas:** 2

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A12.1** | `[-] Bloqueado` | Trail activo entregando logs al bucket de auditoría | — | F1 | P3c | Núcleo |  |
| **A12.2** | `[-] Bloqueado` | Evento buscado y encontrado (ej. StartInstances / cambio de SG) | — | F1 | P3c | Núcleo |  |


<a id="comp-a13"></a>

### Componente A13: Monitoreo AWS: CloudWatch y SNS
- **Fase:** F1 | **Pilar:** P4 | **Total Tareas:** 8

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A13.1** | `[-] Bloqueado` | Dashboard CloudWatch (CPU, red, requests ALB, 5xx) | — | F1 | P4 | Núcleo |  |
| **A13.2** | `[-] Bloqueado` | Alarma: CPU alta en web tier | — | F1 | P4 | Núcleo |  |
| **A13.3** | `[-] Bloqueado` | Alarma: conexiones RDS | — | F1 | P4 | Núcleo |  |
| **A13.4** | `[-] Bloqueado` | Alarma: ALB 5xx | — | F1 | P4 | Núcleo |  |
| **A13.5** | `[-] Bloqueado` | Tópico SNS con suscripción de correo confirmada | — | F1 | P4 | Núcleo |  |
| **A13.6** | `[-] Bloqueado` | Alarma disparada de verdad (carga CPU) y correo recibido | — | F1 | P4 | Núcleo |  |
| **A13.7** | `[-] Bloqueado` | CloudWatch Agent en EC2 (memoria y disco) | — | F1 | P4 | Secundario |  |
| **A13.8** | `[-] Bloqueado` | Log groups de nginx y aplicación | — | F1 | P4 | Secundario |  |


<a id="comp-a14"></a>

### Componente A14: IaC AWS (CloudFormation / módulo Terraform aws_infra)
- **Fase:** F1 | **Pilar:** P5 | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **A14.1** | `[-] Bloqueado` | Stack 1 vpc-stack.yaml (VPC, subredes, SG) desplegado | — | F1 | P5 | Núcleo |  |
| **A14.2** | `[-] Bloqueado` | Stack 2 compute-stack.yaml (EC2, RDS, ALB, ASG) desplegado | — | F1 | P5 | Núcleo |  |
| **A14.3** | `[-] Bloqueado` | Módulo Terraform aws_infra con variables y outputs | — | F1 | P5 | Núcleo |  |
| **A14.4** | `[-] Bloqueado` | terraform apply del módulo aws_infra crea la infraestructura | — | F1 | P5 | Núcleo |  |


---

<a id="dominio-b---oci-home-region-vcn-10200016"></a>

## Dominio B: OCI · Home Region (VCN 10.20.0.0/16)

<a id="comp-b1"></a>

### Componente B1: Red VCN y segmentación
- **Fase:** F2 | **Pilar:** — | **Total Tareas:** 12

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B1.1** | `[x] Completado` | VCN 10.20.0.0/16 creada | — | F2 | — | Núcleo |OCI network vcn list: ninjasec-vcn AVAILABLE, 10.20.0.0/16. OCID: ocid1.vcn.oc1.iad.amaaaaaa3nxgmgaaxc45vda6zodcagfq2sa2uliasla75ray67di4t4gtqca. |
| **B1.2** | `[x] Completado` | Subred pública 10.20.1.0/24 | — | F2 | — | Núcleo | OCI GetSubnet: ninjasec-subnet-edge AVAILABLE, 10.20.1.0/24, prohibit-public-ip-on-vnic=false y prohibit-internet-ingress=false. Conserva su lista de seguridad. OCID: ocid1.subnet.oc1.iad.aaaaaaaa4ok76icpc52hdpwb4o3yuh6dnlwusodrgrf46gxwjbtw736wk5ba. |
| **B1.3** | `[x] Completado` | Subred privada 10.20.10.0/24 | — | F2 | — | Núcleo |OCI network subnet list: ninjasec-subnet-private AVAILABLE, 10.20.10.0/24, prohibit-public-ip-on-vnic=true. OCID: ocid1.subnet.oc1.iad.aaaaaaaazpxp43ofolxis2j6cawsqajxpzqtezchvqpbqjii25ojl3lwv4rq. |
| **B1.4** | `[x] Completado` | Internet Gateway | — | F2 | — | Núcleo | OCI GetInternetGateway: ninjasec-igw AVAILABLE y habilitado. OCID: ocid1.internetgateway.oc1.iad.aaaaaaaa4syvjzl6zou3mfzhahotaora3k67w5z23b57nmsotkz2sc7nys2q. |
| **B1.5** | `[x] Completado` | NAT Gateway para subred privada | — | F2 | — | Núcleo | OCI GetNatGateway: ninjasec-nat AVAILABLE, block-traffic=false. GetRouteTable confirma 0.0.0.0/0 hacia el NAT desde la tabla privada. OCID: ocid1.natgateway.oc1.iad.aaaaaaaajziwatcgix2vmz56wssa7o6oznc7gsuxibvieakfmdem64hh76ba. |
| **B1.6** | `[x] Completado` | Route Tables pública y privada | — | F2 | — | Núcleo | OCI GetSubnet y GetRouteTable: subred publica asociada a ninjasec-rt-edge (ocid1.routetable.oc1.iad.aaaaaaaafhnkfof3unuhkzxjnj7gqvfplmrszff5nnhwrcddcayolrse5ita), 0.0.0.0/0 al IGW. Subred privada asociada a ninjasec-rt-private (ocid1.routetable.oc1.iad.aaaaaaaaarjku7swwx34c6t7a3mfmw7ly3dwomacvzklkrfz2rrshcl35iiq), 0.0.0.0/0 al NAT y servicios regionales al SGW. Se verificaron las asociaciones y destinos en OCI. |
| **B1.7** | `[x] Completado` | Security Lists configuradas | — | F2 | — | Núcleo | OCI GetSecurityList y GetSubnet verificaron las listas asociadas. Ingreso ICMP IPv4 tipo 3/código 4 para PMTU. En la lista privada, salida TCP 22 limitada a las dos IP privadas de B2 para Bastion. El NSG de las VM permite ingreso SSH solo desde el endpoint privado del Bastion. |
| **B1.8** | `[x] Completado` | NSG lb-nsg / monitor-nsg / db-nsg creados | — | F2 | — | Núcleo | OCI ListNetworkSecurityGroups: lb-nsg, ninjasec-nsg-soc (monitor) y ninjasec-nsg-db en estado AVAILABLE en la VCN. lb-nsg: ocid1.networksecuritygroup.oc1.iad.aaaaaaaanasaxkrlu4szysqwp37sz4hwj5hac2gvo27awryyxyfaaf4x5ipa. |
| **B1.9** | `[-] Bloqueado` | db-nsg: 3306 solo desde 10.10.10.0/24 (backend AWS) | — | F2 | — | Núcleo |  |
| **B1.10** | `[x] Completado` | DRG creado y adjunto a la VCN | — | F2 | — | Núcleo | OCI GetDrg y GetDrgAttachment: ninjasec-drg AVAILABLE y ninjasec-drg-vcn ATTACHED a la VCN. Adjunción: ocid1.drgattachment.oc1.iad.aaaaaaaajzqsyqbh2z3pevuxatdpbglcynbggrajisjvjhsubcss2bkjddtq. |
| **B1.11** | `[x] Completado` | Service Gateway | — | F2 | — | Secundario |OCI GetServiceGateway: ninjasec-sgw AVAILABLE, block-traffic=false, servicio regional habilitado. OCID: ocid1.servicegateway.oc1.iad.aaaaaaaakrtor7thqphnupo5sneyumimnkmyc4jryscdyr6arljqfdrlr5vq. |
| **B1.12** | `[x] Completado` | VCN Flow Logs habilitados | — | F2 | — | Secundario | OCI Logging GetLog: ninjasec-vcn-flow ACTIVE y habilitado para la VCN. Retención 30 días y muestreo 1 de 10; captura de tráfico aún sin probar. OCID: ocid1.log.oc1.iad.amaaaaaa3nxgmgaagx5ewsulncrjjcvl3kvciosfhylga2eqqypksmzeitnq. |


<a id="comp-b2"></a>

### Componente B2: Cómputo OCI Always Free
- **Fase:** F2 | **Pilar:** — | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B2.1** | `[x] Completado` | Host de monitoreo en subred privada (A1 Flex o alternativa B2.4) | — | F2 | — | Núcleo | OCI devolvió Out of host capacity para A1 Flex en los tres dominios de Ashburn. Se adoptó bastion-utility-01 (E2.1.Micro) como host de monitoreo. B9.1 a B9.4 verificaron Node Exporter, Prometheus, Grafana por Bastion y /health del portal con HTTP 200. |
| **B2.2** | `[x] Completado` | VM E2.1.Micro bastion/utility | — | F2 | — | Núcleo | OCI GetInstance y GetVnic: bastion-utility-01, VM.Standard.E2.1.Micro, RUNNING en US-ASHBURN-AD-3, subred privada 10.20.10.0/24 sin IP pública. OCID ocid1.instance.oc1.iad.anuwcljt3nxgmgacays7ij4hje7tqwebsgo6wm3mkpwy2cl3veji2ncwaaea. Acceso por OCI Bastion se verifica en B3. |
| **B2.3** | `[x] Completado` | VM E2.1.Micro replica-agent-01 | — | F2 | — | Núcleo | OCI GetInstance y GetVnic: replica-agent-01, VM.Standard.E2.1.Micro, RUNNING en US-ASHBURN-AD-3, subred privada 10.20.10.0/24 sin IP pública. OCID ocid1.instance.oc1.iad.anuwcljt3nxgmgacy6ljbmb5iateotxlcnh5x4hl43o3ywricnav6kav3qla. El agente de replicación se valida en su componente. |
| **B2.4** | `[x] Completado` | Fallback 2×E2.1.Micro si A1 Flex sin capacidad | — | F2 | — | Secundario | OCI GetInstance confirmó dos VM.Standard.E2.1.Micro RUNNING como alternativa: bastion-utility-01 (también destinada a monitoreo) y replica-agent-01. El software de monitoreo queda en B9. |
| **B2.6** | `[x] Completado` | Boot volumes cifrados | — | F2 | — | Núcleo | OCI GetBootVolume verificó los dos volúmenes de 50 GB cifrados en reposo con claves gestionadas por Oracle (kms_key_id=null). GetBootVolumeAttachment confirmó cifrado paravirtualizado en tránsito habilitado en ambos. OCID ocid1.bootvolume.oc1.iad.abuwcljtvs6vnm6g7n7lgvbdtrpcblrq7ugatsj3duc2yyhan3edsryt2qua y ocid1.bootvolume.oc1.iad.abuwcljt6faenvrxsrz3wnzv6uzvypvaqva3jja3y367rga2k7ze5locjjda. |


<a id="comp-b3"></a>

### Componente B3: OCI Bastion Service
- **Fase:** F2 | **Pilar:** — | **Total Tareas:** 3

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B3.1** | `[x] Completado` | Bastion creado en la VCN | — | F2 | — | Núcleo | OCI GetBastion confirmó ninjasec-bastion ACTIVE en la subred privada de la VCN. Endpoint privado 10.20.10.105, acceso limitado a una IP de origen (/32), sesiones de hasta 1800 s. OCID ocid1.bastion.oc1.iad.amaaaaaa3nxgmgaaa6fbn3e4bcmrbb2akgog6jawbjgnoyhdamlgiyznfnwq. |
| **B3.2** | `[x] Completado` | Sesión SSH a monitor-01 solo a través del Bastion | — | F2 | — | Núcleo | Host de monitoreo adoptado por el titular: bastion-utility-01. SSH por OCI Bastion a 10.20.10.36:22 devolvió bastion-utility-01 y opc. Sin IP pública; el NSG limita TCP 22 al endpoint privado del Bastion. |
| **B3.3** | `[x] Completado` | Instancias privadas sin IP pública | — | F2 | — | Núcleo | OCI GetVnic confirmó las dos VM RUNNING en la subred privada 10.20.10.0/24, sin IP pública: bastion-utility-01 (10.20.10.36) y replica-agent-01 (10.20.10.212). |


<a id="comp-b4"></a>

### Componente B4: MySQL HeatWave (BD standby)
- **Fase:** F2 | **Pilar:** P2 | **Total Tareas:** 6

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B4.1** | `[x] Completado` | DB System Always Free (50 GB) en subred privada | — | F2 | P2 | Núcleo | OCI GetDbSystem: ninjasec-mysql-private ACTIVE, MySQL.Free, 50 GiB, AD-3, subred privada 10.20.10.0/24, endpoint privado 10.20.10.191:3306. OCID ocid1.mysqldbsystem.oc1.iad.aaaaaaaaqvrwleeienvokku6d5uuymx5cyxzpy5vqfbtpdvufs3jwskw3spa. |
| **B4.2** | `[-] Bloqueado` | Esquema idéntico al de RDS (tabla incidents) | — | F2 | P2 | Núcleo | Se creó incidents en MySQL de OCI con portal/schema.sql y se verificó su uso mediante CRUD. Sigue pendiente comparar su DDL con RDS cuando se implemente A9.7. |
| **B4.3** | `[x] Completado` | Usuario de aplicación y permisos creados | — | F2 | P2 | Núcleo | SHOW GRANTS confirmó SELECT, INSERT, UPDATE y DELETE sobre ninjasec.* para ninjasec_app@10.20.10.36. SELECT CURRENT_USER(), DATABASE(), 1 devolvió ninjasec_app@10.20.10.36, ninjasec, 1. Cuenta limitada a la Micro de OCI y con TLS obligatorio. El acceso de AWS se validará en su integración. |
| **B4.4** | `[x] Completado` | Acceso 3306 restringido por NSG | — | F2 | P2 | Núcleo | OCI Work Request de asociación del NSG SUCCEEDED. GetDbSystem y ListNetworkSecurityGroupSecurityRules confirmaron que ninjasec-nsg-db permite TCP 3306 solo desde 10.20.10.36/32. La política IAM está limitada al principal del DB System. OCID de política ocid1.policy.oc1..aaaaaaaaecb5ohnondn574cvtjgxxjkl6xt5i5dm4wwvinarsmhoubbnzxxa. El acceso del backend AWS sigue pendiente en B1.9. |
| **B4.5** | `[x] Completado` | Conexión exitosa desde monitor-01 | — | F2 | P2 | Núcleo | Desde el host de monitoreo adoptado bastion-utility-01, SELECT VERSION() devolvió 26.10.0-u1-cloud y la cuenta de aplicación ejecutó SELECT con TLS_AES_128_GCM_SHA256. |
| **B4.6** | `[x] Completado` | Backup automático habilitado | — | F2 | P2 | Núcleo | OCI GetDbSystem en estado ACTIVE confirmó backupPolicy.isEnabled=true y retentionInDays=1 (MySQL.Free). |


<a id="comp-b5"></a>

### Componente B5: OCI Flexible Load Balancer (endpoint de failover)
- **Fase:** F2 | **Pilar:** P3b | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B5.1** | `[x] Completado` | LB Flexible 10 Mbps en subred pública | — | F2 | P3b | Núcleo | OCI GetLoadBalancer: ninjasec-oci-lb ACTIVE y público, Flexible 10/10 Mbps, asociado a la subred regional pública 10.20.1.0/24. IP 129.159.170.148. OCID ocid1.loadbalancer.oc1.iad.aaaaaaaahzdbqrm4x6y2jlunz26wjwc5rcv6ujcyhvq342pvg4d6t4whe67a. |
| **B5.2** | `[x] Completado` | Backend set con health check | — | F2 | P3b | Núcleo | GetHealthChecker: ninjasec-standby usa HTTP /health en 8080 y espera 200. OCI GetBackendHealth confirmó OK en 10.20.10.36:8080; /health también respondió 200 por el LB. |
| **B5.3** | `[x] Completado` | Backend standby que sirve el portal NINJA-SEC desde OCI | — | F2 | P3b | Núcleo | Portal de incidentes en portal/, desplegado como servicio systemd habilitado en bastion-utility-01 (10.20.10.36:8080), con MySQL privado y backend OCI OK. Prueba HTTPS confirmó creación 201, lectura y edición 200, borrado 204 y consulta posterior 404. Se eliminó el registro temporal. |
| **B5.4** | `[x] Completado` | Listener HTTP/HTTPS configurado | — | F2 | P3b | Núcleo | Listeners HTTP 80 y HTTPS 443. La regla ninjasec_force_https devolvió 301 a HTTPS. El NSG público admite 80/443. La prueba HTTPS desde OCI validó el certificado temporal autofirmado para la IP y el listener mantiene TLS 1.2/1.3. |
| **B5.5** | `[x] Completado` | Portal accesible vía IP del LB OCI | — | F2 | P3b | Núcleo | GET https://129.159.170.148/ desde la Micro de OCI con certificado temporal validado: portal 200 con autenticación y 401 sin credenciales. /portal.js y /health respondieron 200. CRUD de prueba completado por el mismo endpoint. |


<a id="comp-b6"></a>

### Componente B6: OCI Vault
- **Fase:** F2 | **Pilar:** — | **Total Tareas:** 3

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B6.1** | `[x] Completado` | Vault y master key creados | — | F2 | — | Núcleo | OCI GetVault confirmó DEFAULT ACTIVE (ocid1.vault.oc1.iad.ejvpiepoaafcs.abuwcljtj6lxek3efr77dudlguntvnyctszx5yjnfdihfuh5ivm4mqw6p7ra). GetKey confirmó AES-256 SOFTWARE ENABLED (ocid1.key.oc1.iad.ejvpiepoaafcs.abuwcljr56kcgdgzeyxjfwsapkrozwwwlul3o4pnvd6khryledvawlpipgoa). |
| **B6.2** | `[x] Completado` | Secreto de MySQL HeatWave almacenado | — | F2 | — | Núcleo | OCI GetSecret confirmó ACTIVE (ocid1.vaultsecret.oc1.iad.amaaaaaa3nxgmgaax2asqrwadm6ll3uq47bzykuef263eyz3zlw6cksjv4ca) y GetSecretBundle CURRENT coincidió con la credencial de aplicación protegida localmente. No se imprimió el contenido. |
| **B6.3** | `[x] Completado` | Scripts referencian el OCID del secreto (sin credenciales en texto) | — | F2 | — | Núcleo | La VM bastion-utility-01 leyó CURRENT por OCID con identidad de instancia y política limitada al secreto MySQL (ocid1.policy.oc1..aaaaaaaapvcu7r7dvaaxpac6sorjqugcznmiwuaafzyq3wp72f6lw6siwohq). Después del reinicio, portal /health y exportador MySQL /metrics respondieron 200. Se verificó DB_SECRET_OCID y ausencia de DB_USER y DB_PASSWORD en ambos procesos. Backend OCI en OK. |


<a id="comp-b7"></a>

### Componente B7: OCI Object Storage (staging de backups)
- **Fase:** F2 | **Pilar:** P3c | **Total Tareas:** 3

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B7.1** | `[x] Completado` | Bucket de staging de backups creado | — | F2 | P3c | Núcleo | OCI GetBucket confirmó ninjasec-backup-staging, clase Standard. OCID ocid1.bucket.oc1.iad.aaaaaaaanxtwvfzjolyk36p7iubykkpheqxwxrhyhwrquklcm5b2d5m6eo2a. |
| **B7.2** | `[x] Completado` | Bucket privado y cifrado | — | F2 | P3c | Núcleo | OCI GetBucket confirmó publicAccessType=NoPublicAccess y cifrado AES-256 de Object Storage con clave gestionada por Oracle. |
| **B7.3** | `[x] Completado` | Backup de MySQL depositado en el bucket | — | F2 | P3c | Núcleo | Respaldo lógico de ninjasec.incidents depositado en ninjasec-backup-staging/mysql/ninjasec-20261111T070855Z-cf90ae215883.sql.gz (392 bytes). Se descargó, descomprimió y verificó el SHA-256 cf90ae215883e35699362711bf074394ca4d559e8f35e2f0e01f30531e78bd27. La tabla tenía 0 filas. No se realizó restauración. |


<a id="comp-b8"></a>

### Componente B8: Monitoreo OCI
- **Fase:** F2 | **Pilar:** P4 | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B8.1** | `[x] Completado` | OCI Monitoring con métricas de compute visibles | — | F2 | P4 | Núcleo | OCI SummarizeMetricsData devolvió puntos reales de CpuUtilization en oci_vmi_resource_utilization para bastion-utility-01 y replica-agent-01. La muestra de las 07:14 UTC devolvió 1.48 % y 1.37 %, respectivamente. |
| **B8.2** | `[x] Completado` | Alarma CPU > 80% | — | F2 | P4 | Núcleo | OCI GetAlarm confirmó dos alarmas habilitadas con CpuUtilization[5m].mean() > 80, filtradas por OCID de instancia y dirigidas al topic ninjasec-monitoring-alerts. Monitor: ocid1.alarm.oc1.iad.amaaaaaa3nxgmgaaynhesiwqvbzkxny4432igfamrjl6uwvcxjvmv25v6y2q. Réplica: ocid1.alarm.oc1.iad.amaaaaaa3nxgmgaamd5ilwa2wivvzzvk4doixzt7nqts74uhc2uuykahjzta. |
| **B8.3** | `[x] Completado` | Topic de Notifications con correo suscrito | — | F2 | P4 | Núcleo | OCI GetTopic y GetSubscription confirmaron topic y suscripción EMAIL en estado ACTIVE después de la confirmación del destinatario. Topic ocid1.onstopic.oc1.iad.amaaaaaa3nxgmgaaxikr6t2szrwyitk7eicxdiuhkncemdewzhlm6qropqlq. |
| **B8.4** | `[x] Completado` | Alarma disparada y correo recibido | — | F2 | P4 | Núcleo | Prueba controlada de entrega en el mismo topic. GetAlarmHistory registró OK a FIRING el 2026-11-11 a las 07:20:30 UTC. El destinatario confirmó el correo OK_TO_FIRING con lectura de CPU de 1.49 % y umbral temporal > 0. Alarma ocid1.alarm.oc1.iad.amaaaaaa3nxgmgaatrt5km5przlyiw2cyqslegp5me7ymvdlaqg72ookekdq, deshabilitada al terminar. Las dos alarmas operativas conservan el umbral > 80 %.  |
| **B8.5** | `[x] Completado` | Logging habilitado (VCN Flow Logs / audit) | — | F2 | P4 | Secundario | OCI Logging GetLog confirmó ninjasec-vcn-flow ACTIVE y habilitado para la VCN. OCI Audit ListEvents devolvió 78 eventos en una ventana de dos horas. Log ocid1.log.oc1.iad.amaaaaaa3nxgmgaagx5ewsulncrjjcvl3kvciosfhylga2eqqypksmzeitnq. |


<a id="comp-b9"></a>

### Componente B9: SOC Dashboard: Grafana + Prometheus (monitor-01)
- **Fase:** F3 | **Pilar:** P4 | **Total Tareas:** 15

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B9.1** | `[x] Completado` | Prometheus instalado y scrapeando | — | F3 | P4 | Núcleo | Prometheus 3.13.5 activo por systemd en bastion-utility-01, escuchando solo en 127.0.0.1:9090. GET /api/v1/targets confirmó node=up y prometheus=up. El portal continuó con /health=200 durante la prueba. |
| **B9.2** | `[x] Completado` | node_exporter activo | — | F3 | P4 | Núcleo | Node Exporter 1.12.1 activo por systemd en 127.0.0.1:9100. GET /metrics devolvió node_memory_MemAvailable_bytes y Prometheus confirmó node=up. La Micro reportó 375800 kB de MemAvailable durante la prueba. |
| **B9.3** | `[x] Completado` | Grafana 10 instalado y accesible de forma segura (no expuesto sin control) | — | F3 | P4 | Núcleo | Grafana 10.4.19+security-01 activo por systemd, ligado solo a 127.0.0.1:3000 en bastion-utility-01. Por túnel OCI Bastion, GET /api/health devolvió 200 con base local OK y GET /api/datasources sin credenciales devolvió 401. Sin listener público. |
| **B9.4** | `[x] Completado` | Datasource Prometheus | — | F3 | P4 | Núcleo | Grafana datasource Prometheus OCI (UID ninjasec-oci-prom) usa 127.0.0.1:9090. Su API autenticada devolvió up{job=node}=1. Con Grafana, Prometheus, Node Exporter y portal activos, /health del portal devolvió 200 y la Micro reportó 422648 kB de MemAvailable durante la prueba. |
| **B9.5** | `[-] Bloqueado` | Datasource CloudWatch (credenciales del Lab) | — | F3 | P4 | Núcleo |  |
| **B9.6** | `[x] Completado` | Plugin / datasource OCI Metrics | — | F3 | P4 | Núcleo | Grafana cargó el plugin Oracle OCI Metrics 6.5.6 con firma valid. El datasource ninjasec-oci-native usa identidad de instancia y política de solo lectura. POST /api/ds/query devolvió 6 puntos de CpuUtilization en oci_vmi_resource_utilization, sin errores. |
| **B9.7** | `[-] Bloqueado` | Datasource Azure Monitor | — | F3 | P4 | Núcleo |  |
| **B9.8** | `[-] Bloqueado` | Panel 1: requests/seg del ALB | — | F3 | P4 | Núcleo |  |
| **B9.9** | `[-] Bloqueado` | Panel 2: CPU promedio EC2 | — | F3 | P4 | Núcleo |  |
| **B9.10** | `[x] Completado` | Panel 3: conexiones MySQL (OCI) | — | F3 | P4 | Núcleo | Panel 3 Conexiones MySQL (OCI), tablero UID ninjasec-oci-overview. Exportador local consulta Threads_connected con TLS. Grafana consultó ninjasec_mysql_threads_connected mediante Prometheus y devolvió 3 conexiones. El portal respondió HTTP 200. |
| **B9.11** | `[-] Bloqueado` | Panel 4: replication lag | — | F3 | P4 | Núcleo |  |
| **B9.12** | `[-] Bloqueado` | Panel 5: bloqueos del WAF | — | F3 | P4 | Núcleo |  |
| **B9.13** | `[-] Bloqueado` | Panel 6: últimos logs de Azure Log Analytics | — | F3 | P4 | Núcleo |  |
| **B9.14** | `[-] Bloqueado` | Chequeo de estado del túnel VPN (ping checker) en Prometheus | — | F3 | P4 | Núcleo |  |
| **B9.15** | `[x] Completado` | Alarma visible en Grafana | — | F3 | P4 | Núcleo | Regla nativa de Grafana ninjasec-oci-cpu-grafana: CPU > 80 %, visible en el panel 15 del tablero ninjasec-oci-overview. GET /api/prometheus/grafana/api/v1/rules confirmó evaluación con health=ok, state=inactive, sin error. Las alarmas de correo de OCI se verificaron en B8. |


<a id="comp-b10"></a>

### Componente B10: IaC OCI (módulo Terraform oci_infra / Resource Manager)
- **Fase:** F2 | **Pilar:** P5 | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **B10.1** | `[x] Completado` | Módulo oci_infra con variables y outputs | — | F2 | P5 | Núcleo | Módulo terraform/modules/oci_infra con variables y outputs para VCN, subredes, gateways, rutas, NSG, Compute, MySQL.Free y LB. Terraform 1.13.5 y oracle/oci 7.32.0: terraform validate devolvió Success en replica-agent-01. |
| **B10.2** | `[x] Completado` | Autenticación OCI vía API key fuera del repositorio | — | F2 | P5 | Núcleo | Perfil local NINJA_SEC_TERRAFORM fuera del repositorio; clave privada con ACL exclusiva del usuario de Windows. Firma API Key verificada con GetVcn HTTP 200 para ninjasec-vcn, fingerprint 37:ea:8e:8f:e4:a1:f4:27:ed:1f:c2:8b:3d:6d:cd:9a. |
| **B10.3** | `[x] Completado` | terraform apply crea VCN + NSG + compute + HeatWave + LB | — | F2 | P5 | Núcleo | 11-nov-2026, Ashburn. Stack aislado ninjasec-b10-apply-proof (ocid1.ormstack.oc1.iad.amaaaaaa3nxgmgaatgoa7tl3zbqmjgsy6gkiehdpt76cbe3ktaylmsagkcmq), Terraform 1.5.x / oracle/oci 7.32.0. PLAN ocid1.ormjob.oc1.iad.amaaaaaa3nxgmgaahsmlv4sludjfof4elwzdsu3aaq4a44ejra3gzi3cbsua: 18 altas. Primer APPLY ocid1.ormjob.oc1.iad.amaaaaaa3nxgmgaanxhjxjxbkbmroxa35mfwfshjtz647bv3qwpklrotlu3q: 16 creados; MySQL rechazó la longitud de la contraseña temporal. APPLY corregido ocid1.ormjob.oc1.iad.amaaaaaa3nxgmgaad7ebqun72zn323tg5llxyduofkhwqm4xhqbs7dhzbdka: SUCCEEDED, 2 altas, 0 cambios, 0 eliminaciones; estado total 18 recursos. Verificación API: VCN 10.29.0.0/16 AVAILABLE (ocid1.vcn.oc1.iad.amaaaaaa3nxgmgaa2exwdngoziw5pwhh2kzavhqkwxbwhzhhrfkuqk7ys3oa); 4 NSG AVAILABLE (OCID de app ocid1.networksecuritygroup.oc1.iad.aaaaaaaawgw4e57pu7skelyih7d2iyqeyhcisnnylcxgih3w5pn42ian4bhq; todos en outputs nsg_ids); VM E5 Flex RUNNING y privada (ocid1.instance.oc1.iad.anuwcljt3nxgmgacioadxtjnh7mneqxmsbkgb6onnykbcd25gecrypbtfyqa); MySQL.2 ACTIVE (ocid1.mysqldbsystem.oc1.iad.aaaaaaaapkrrvxrbdnlrv52sgs2qnxvkqhwrooh5rt54z23gmfglvpqnn37q) con HeatWave.32GB cluster-node-1 ACTIVE (GetHeatWaveCluster con OCID de MySQL); LB ACTIVE (ocid1.loadbalancer.oc1.iad.aaaaaaaaaig7ijo66mmbmrog4v76omzojjxkh5rpur4chh7bq4i6wxpmpixa). DESTROY ocid1.ormjob.oc1.iad.amaaaaaa3nxgmgaa6ac4atphzhnj7hxzftgfel5qfrej2ryqk7mehq5nalqa: SUCCEEDED, 18 eliminados, estado Terraform vacío y volumen de arranque TERMINATED; base y balanceador del portal ACTIVE tras la limpieza. |
| **B10.4** | `[x] Completado` | Stack equivalente en OCI Resource Manager | — | F2 | P5 | Secundario | Stack ninjasec-oci-infra ACTIVE (ocid1.ormstack.oc1.iad.amaaaaaa3nxgmgaa7fwbd3z3tvdjdxa7gjypi4i7ayxmln26rdbgwd3ykgiq); job PLAN SUCCEEDED (ocid1.ormjob.oc1.iad.amaaaaaa3nxgmgaabubmols3kcbt73wwzpdf7vuuwtjej47reop3osigjnqq) con Terraform 1.5.x y oracle/oci 7.32.0: 18 altas, 0 cambios y 0 eliminaciones, incluidos VCN, NSG, Compute, MySQL.Free y LB. |


---

<a id="dominio-c---azure-east-us-cumplimiento-y-forense"></a>

## Dominio C: Azure · East US (cumplimiento y forense)

<a id="comp-c1"></a>

### Componente C1: Azure Blob Storage con inmutabilidad WORM
- **Fase:** F2 | **Pilar:** P3c | **Total Tareas:** 10

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **C1.1** | `[x] Completado` | Resource Group rg-ninjasec-compliance | — | F2 | P3c | Núcleo | az group list confirma rg-ninjasec-compliance, eastus. |
| **C1.2** | `[x] Completado` | Storage Account creada | — | F2 | P3c | Núcleo | az storage account show: ninjaseccompliance63ba, westus, Standard_LRS, Succeeded, TLS1_2, solo HTTPS y allowBlobPublicAccess=false. |
| **C1.3** | `[x] Completado` | Container audit-logs-aws | — | F2 | P3c | Núcleo | az storage container-rm list: audit-logs-aws, publicAccess=None. |
| **C1.4** | `[x] Completado` | Container audit-logs-oci | — | F2 | P3c | Núcleo | az storage container-rm list: audit-logs-oci, publicAccess=None. |
| **C1.5** | `[x] Completado` | Container db-backups | — | F2 | P3c | Núcleo | az storage container-rm list: db-backups, publicAccess=None. |
| **C1.6** | `[x] Completado` | Immutability Policy 365 días bloqueada en audit-logs-aws | — | F2 | P3c | Núcleo | az storage container immutability-policy show: audit-logs-aws, 365 días, Locked. |
| **C1.7** | `[x] Completado` | Immutability Policy 365 días bloqueada en audit-logs-oci | — | F2 | P3c | Núcleo | az storage container immutability-policy show: audit-logs-oci, 365 días, Locked. |
| **C1.8** | `[x] Completado` | Immutability Policy 30 días bloqueada en db-backups | — | F2 | P3c | Núcleo | az storage container immutability-policy show: db-backups, 30 días, Locked. |
| **C1.9** | `[x] Completado` | Intento de borrar un blob → error 409 BlobImmutableDueToPolicy | — | F2 | P3c | Núcleo | DELETE autenticado de ninjasec-worm-proof-20261111-192554.txt en audit-logs-oci: HTTP 409 BlobImmutableDueToPolicy. |
| **C1.10** | `[x] Completado` | SAS token de mínimo privilegio con expiración | — | F2 | P3c | Núcleo | SAS de delegación para un solo blob en audit-logs-oci, solo HTTPS, permiso c (crear), vencimiento 2026-11-11 19:45 UTC. PUT 201 y GET 403. Permisos temporales de prueba retirados. |


<a id="comp-c2"></a>

### Componente C2: Log Analytics (panel de cumplimiento)
- **Fase:** F3 | **Pilar:** P3c | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **C2.1** | `[x] Completado` | Workspace de Log Analytics creado | — | F3 | P3c | Núcleo | az monitor log-analytics workspace show: ninjasec-law, westus, Succeeded, retención 30 días. |
| **C2.2** | `[-] Bloqueado` | Ingesta de eventos de CloudTrail (AWS) | — | F3 | P3c | Núcleo |  |
| **C2.3** | `[-] Bloqueado` | Ingesta de OCI Audit logs | — | F3 | P3c | Núcleo |  |
| **C2.4** | `[-] Bloqueado` | Consulta KQL forense (ej. SG modificados en 24 h) devuelve resultados | — | F3 | P3c | Núcleo |  |
| **C2.5** | `[ ] Pendiente` | Workbook/dashboard de cumplimiento | — | F3 | P3c | Secundario | az resource show confirma ninjasec-compliance-workbook (5ec9a0d2-1a5a-4e81-a7a4-698f9e43b035) asociado a ninjasec-law. Falta verificar las visualizaciones con eventos reales. |


<a id="comp-c3"></a>

### Componente C3: IaC Azure (módulo Terraform azure_storage)
- **Fase:** F2 | **Pilar:** P5 | **Total Tareas:** 2

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **C3.1** | `[ ] Pendiente` | Módulo azure_storage con variables y outputs | — | F2 | P5 | Núcleo |  |
| **C3.2** | `[ ] Pendiente` | terraform apply crea RG + Blob + WORM + Log Analytics | — | F2 | P5 | Núcleo |  |


---

<a id="dominio-d---cloudflare-dns-y-borde"></a>

## Dominio D: Cloudflare · DNS y borde

<a id="comp-d1"></a>

### Componente D1: DNS y failover
- **Fase:** F3 | **Pilar:** P3b | **Total Tareas:** 7

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **D1.1** | `[ ] Pendiente` | Zona del dominio activa en Cloudflare | — | F3 | P3b | Núcleo |  |
| **D1.2** | `[-] Bloqueado` | Registro primario (CNAME) hacia el ALB de AWS | — | F3 | P3b | Núcleo |  |
| **D1.3** | `[-] Bloqueado` | Registro secundario hacia el LB de OCI | — | F3 | P3b | Núcleo |  |
| **D1.4** | `[ ] Pendiente` | Proxy y TLS de Cloudflare configurados | — | F3 | P3b | Núcleo |  |
| **D1.5** | `[-] Bloqueado` | Mecanismo de failover definido (health check o cambio manual) | — | F3 | P3b | Núcleo |  |
| **D1.6** | `[-] Bloqueado` | portal.<dominio> resuelve y sirve el portal por HTTPS | — | F3 | P3b | Núcleo |  |
| **D1.7** | `[-] Bloqueado` | Route 53 Health Check + Failover (solo si Academy lo permite) | — | F3 | P3b | Secundario |  |


---

<a id="dominio-m---integraciones-multicloud"></a>

## Dominio M: Integraciones Multicloud

<a id="comp-m1"></a>

### Componente M1: Backbone VPN IPSec AWS ↔ OCI
- **Fase:** F3 | **Pilar:** P1 | **Total Tareas:** 11

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M1.1** | `[-] Bloqueado` | Virtual Private Gateway creado y adjunto a la VPC | — | F3 | P1 | Núcleo |  |
| **M1.2** | `[-] Bloqueado` | Customer Gateway apuntando a la IP pública del DRG de OCI | — | F3 | P1 | Núcleo |  |
| **M1.3** | `[-] Bloqueado` | Site-to-Site VPN en OCI con CPE = AWS | — | F3 | P1 | Núcleo |  |
| **M1.4** | `[-] Bloqueado` | Túnel IPSec en estado UP (ambos lados) | — | F3 | P1 | Núcleo |  |
| **M1.5** | `[-] Bloqueado` | AWS: 10.20.0.0/16 → VGW en route tables privadas | — | F3 | P1 | Núcleo |  |
| **M1.6** | `[-] Bloqueado` | OCI: 10.10.0.0/16 → DRG en route tables | — | F3 | P1 | Núcleo |  |
| **M1.7** | `[-] Bloqueado` | SG/NSG permiten 3306 entre 10.10.10.0/24 y 10.20.10.0/24 | — | F3 | P1 | Núcleo |  |
| **M1.8** | `[-] Bloqueado` | ping 10.20.10.20 desde app-backend responde | — | F3 | P1 | Núcleo |  |
| **M1.9** | `[-] Bloqueado` | ip route en app-backend muestra la ruta hacia 10.20.x.x | — | F3 | P1 | Núcleo |  |
| **M1.10** | `[-] Bloqueado` | Plan B: WireGuard en EC2 (si no hay VGW) | — | F3 | P1 | Secundario |  |
| **M1.11** | `[-] Bloqueado` | Segundo túnel de redundancia | — | F3 | P1 | Secundario |  |


<a id="comp-m2"></a>

### Componente M2: Replicación de BD RDS → MySQL HeatWave
- **Fase:** F3 | **Pilar:** P2 | **Total Tareas:** 7

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M2.1** | `[-] Bloqueado` | Usuario de replicación creado en RDS | — | F3 | P2 | Núcleo |  |
| **M2.2** | `[-] Bloqueado` | binlog ROW activo con retención suficiente | — | F3 | P2 | Núcleo |  |
| **M2.3** | `[-] Bloqueado` | Carga inicial consistente importada en HeatWave | — | F3 | P2 | Núcleo |  |
| **M2.4** | `[-] Bloqueado` | Replicación configurada (RDS como fuente, vía VPN) | — | F3 | P2 | Núcleo |  |
| **M2.5** | `[-] Bloqueado` | Replicación en ejecución (hilos IO/SQL activos) | — | F3 | P2 | Núcleo |  |
| **M2.6** | `[-] Bloqueado` | Replication lag < 2 s medido | — | F3 | P2 | Núcleo |  |
| **M2.7** | `[-] Bloqueado` | INSERT en AWS → SELECT en OCI verificado | — | F3 | P2 | Núcleo |  |


<a id="comp-m3"></a>

### Componente M3: Dual-write de la aplicación
- **Fase:** F2 | **Pilar:** P2 | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M3.1** | `[-] Bloqueado` | Lógica dual-write en app-backend (RDS + HeatWave) | — | F2 | P2 | Núcleo |  |
| **M3.2** | `[-] Bloqueado` | Etapa interina: escritura a HeatWave con TLS por IP pública | — | F2 | P2 | Núcleo |  |
| **M3.3** | `[-] Bloqueado` | Migrado a IP privada 10.20.10.20 vía VPN | — | F2 | P2 | Núcleo |  |
| **M3.4** | `[-] Bloqueado` | Manejo de fallo parcial (si una BD falla, la app no se cae) | — | F2 | P2 | Núcleo |  |
| **M3.5** | `[-] Bloqueado` | Ticket creado en el portal visible en OCI en < 1 s | — | F2 | P2 | Núcleo |  |


<a id="comp-m4"></a>

### Componente M4: Failover de base de datos
- **Fase:** F4 | **Pilar:** P2 | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M4.1** | `[-] Bloqueado` | Connection string conmutable (secreto/variable de entorno) | — | F4 | P2 | Núcleo |  |
| **M4.2** | `[-] Bloqueado` | Detección de falla de RDS en la aplicación | — | F4 | P2 | Núcleo |  |
| **M4.3** | `[-] Bloqueado` | Conmutación a HeatWave ejecutada | — | F4 | P2 | Núcleo |  |
| **M4.4** | `[-] Bloqueado` | Con RDS detenido el portal sigue operativo con los datos | — | F4 | P2 | Núcleo |  |


<a id="comp-m5"></a>

### Componente M5: Failover de tráfico AWS ↔ OCI
- **Fase:** F3 | **Pilar:** P3b | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M5.1** | `[-] Bloqueado` | Portal standby operativo en OCI | — | F3 | P3b | Núcleo |  |
| **M5.2** | `[-] Bloqueado` | Cloudflare redirige al LB de OCI al caer el endpoint AWS | — | F3 | P3b | Núcleo |  |
| **M5.3** | `[-] Bloqueado` | Prueba real: AWS fuera de servicio → portal servido desde OCI | — | F3 | P3b | Núcleo |  |
| **M5.4** | `[-] Bloqueado` | Retorno a AWS verificado | — | F3 | P3b | Núcleo |  |


<a id="comp-m6"></a>

### Componente M6: Pipeline de backups hacia Azure
- **Fase:** F2 | **Pilar:** P3c | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M6.1** | `[ ] Pendiente` | Script mysqldump programado (cron) | — | F2 | P3c | Núcleo |  |
| **M6.2** | `[ ] Pendiente` | Dump depositado en OCI Object Storage | — | F2 | P3c | Núcleo |  |
| **M6.3** | `[-] Bloqueado` | Copia subida a Azure container db-backups (WORM) | — | F2 | P3c | Núcleo |  |
| **M6.4** | `[-] Bloqueado` | Archivos visibles en ambos destinos | — | F2 | P3c | Núcleo |  |
| **M6.5** | `[-] Bloqueado` | Restauración desde el dump verificada | — | F2 | P3c | Núcleo |  |


<a id="comp-m7"></a>

### Componente M7: Pipeline forense CloudTrail → Azure
- **Fase:** F3 | **Pilar:** P3c | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M7.1** | `[-] Bloqueado` | Script boto3 lee logs de CloudTrail desde S3 | — | F3 | P3c | Núcleo |  |
| **M7.2** | `[-] Bloqueado` | Cron diario (02:00) sube a audit-logs-aws | — | F3 | P3c | Núcleo |  |
| **M7.3** | `[-] Bloqueado` | Blob queda bloqueado por política WORM | — | F3 | P3c | Núcleo |  |
| **M7.4** | `[-] Bloqueado` | Eventos enviados a Log Analytics | — | F3 | P3c | Núcleo |  |


<a id="comp-m8"></a>

### Componente M8: Pipeline forense OCI Audit → Azure
- **Fase:** F3 | **Pilar:** P3c | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M8.1** | `[ ] Pendiente` | Script OCI CLI exporta OCI Audit logs | — | F3 | P3c | Núcleo |  |
| **M8.2** | `[-] Bloqueado` | Cron diario (02:30) sube a audit-logs-oci | — | F3 | P3c | Núcleo |  |
| **M8.3** | `[-] Bloqueado` | Blob queda bloqueado por política WORM | — | F3 | P3c | Núcleo |  |
| **M8.4** | `[-] Bloqueado` | Eventos enviados a Log Analytics | — | F3 | P3c | Núcleo |  |


<a id="comp-m9"></a>

### Componente M9: Observabilidad cruzada (Grafana)
- **Fase:** F3 | **Pilar:** P4 | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M9.1** | `[-] Bloqueado` | Métricas de CloudWatch (AWS) visibles en Grafana OCI | — | F3 | P4 | Núcleo |  |
| **M9.2** | `[-] Bloqueado` | Métricas de OCI visibles en Grafana | — | F3 | P4 | Núcleo |  |
| **M9.3** | `[-] Bloqueado` | Datos de Azure Log Analytics visibles en Grafana | — | F3 | P4 | Núcleo |  |
| **M9.4** | `[-] Bloqueado` | Dashboard unificado de las 3 nubes con datos en vivo | — | F3 | P4 | Núcleo |  |


<a id="comp-m10"></a>

### Componente M10: Terraform multi-provider (repo único)
- **Fase:** F2 | **Pilar:** P5 | **Total Tareas:** 7

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **M10.1** | `[ ] Pendiente` | providers.tf con AWS + OCI + AzureRM | — | F2 | P5 | Núcleo |  |
| **M10.2** | `[-] Bloqueado` | Backend remoto S3 + lock DynamoDB funcionando | — | F2 | P5 | Núcleo |  |
| **M10.3** | `[ ] Pendiente` | main.tf invoca los 3 módulos | — | F2 | P5 | Núcleo |  |
| **M10.4** | `[ ] Pendiente` | terraform plan sin errores | — | F2 | P5 | Núcleo |  |
| **M10.5** | `[-] Bloqueado` | terraform apply despliega las 3 nubes | — | F2 | P5 | Núcleo |  |
| **M10.6** | `[-] Bloqueado` | terraform destroy elimina los recursos | — | F2 | P5 | Núcleo |  |
| **M10.7** | `[-] Bloqueado` | Re-apply recrea la infraestructura (~10 min) | — | F2 | P5 | Núcleo |  |


---

<a id="dominio-t---seguridad-transversal"></a>

## Dominio T: Seguridad transversal

<a id="comp-t1"></a>

### Componente T1: Cifrado
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 7

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **T1.1** | `[-] Bloqueado` | En reposo: EBS cifrado | — | F1 | — | Núcleo |  |
| **T1.2** | `[-] Bloqueado` | En reposo: RDS cifrado | — | F1 | — | Núcleo |  |
| **T1.3** | `[-] Bloqueado` | En reposo: S3 con SSE-KMS | — | F1 | — | Núcleo |  |
| **T1.4** | `[-] Bloqueado` | En reposo: volúmenes OCI cifrados | — | F1 | — | Núcleo |  |
| **T1.5** | `[-] Bloqueado` | En tránsito: HTTPS en ALB / Cloudflare | — | F1 | — | Núcleo |  |
| **T1.6** | `[-] Bloqueado` | En tránsito: tráfico AWS↔OCI por túnel IPSec | — | F1 | — | Núcleo |  |
| **T1.7** | `[-] Bloqueado` | En tránsito: TLS en conexiones BD interinas | — | F1 | — | Núcleo |  |


<a id="comp-t2"></a>

### Componente T2: Higiene de secretos
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **T2.1** | `[-] Bloqueado` | grep -r "password | secret | key" sobre el repositorio sin hallazgos | — | Núcleo |  |
| **T2.2** | `[ ] Pendiente` | terraform.tfvars y llaves fuera de Git | — | F1 | — | Núcleo |  |
| **T2.3** | `[-] Bloqueado` | Credenciales de datasources de Grafana fuera del repositorio | — | F1 | — | Núcleo |  |
| **T2.4** | `[-] Bloqueado` | Procedimiento de refresco de credenciales del Lab (CLI, Terraform, Grafana) | — | F1 | — | Núcleo |  |


<a id="comp-t3"></a>

### Componente T3: Hardening y acceso administrativo
- **Fase:** F2 | **Pilar:** — | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **T3.1** | `[-] Bloqueado` | SSH solo por llave (sin contraseña) en todas las VMs | — | F2 | — | Núcleo |  |
| **T3.2** | `[-] Bloqueado` | Administración de OCI solo vía Bastion Service | — | F2 | — | Núcleo |  |
| **T3.3** | `[ ] Pendiente` | Servidores sin puertos de administración abiertos a Internet | — | F2 | — | Núcleo |  |
| **T3.4** | `[-] Bloqueado` | Paquetes del SO actualizados | — | F2 | — | Núcleo |  |
| **T3.5** | `[-] Bloqueado` | fail2ban o equivalente en hosts expuestos | — | F2 | — | Secundario |  |


<a id="comp-t4"></a>

### Componente T4: Identidad y políticas
- **Fase:** F2 | **Pilar:** — | **Total Tareas:** 4

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **T4.1** | `[-] Bloqueado` | AWS: LabRole con políticas de recurso (bucket, secreto, KMS) | — | F2 | — | Núcleo |  |
| **T4.2** | `[ ] Pendiente` | OCI: grupo de operación creado | — | F2 | — | Núcleo |  |
| **T4.3** | `[ ] Pendiente` | OCI: políticas de mínimo privilegio aplicadas | — | F2 | — | Núcleo |  |
| **T4.4** | `[ ] Pendiente` | Azure: RBAC mínimo sobre la Storage Account | — | F2 | — | Núcleo |  |


---

<a id="dominio-r---continuidad-backup-y-dr"></a>

## Dominio R: Continuidad: Backup y DR

<a id="comp-r1"></a>

### Componente R1: Respaldos operativos
- **Fase:** F4 | **Pilar:** P2 | **Total Tareas:** 3

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **R1.1** | `[-] Bloqueado` | Backup automático de RDS (7 días) verificado en consola | — | F4 | P2 | Núcleo |  |
| **R1.2** | `[-] Bloqueado` | Snapshot manual de RDS tomado | — | F4 | P2 | Núcleo |  |
| **R1.3** | `[-] Bloqueado` | Versionado de S3 verificado (recuperar objeto previo) | — | F4 | P2 | Núcleo |  |


<a id="comp-r2"></a>

### Componente R2: Recuperaciones probadas
- **Fase:** F4 | **Pilar:** P2 | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **R2.1** | `[-] Bloqueado` | Restauración de RDS desde snapshot probada | — | F4 | P2 | Núcleo |  |
| **R2.2** | `[-] Bloqueado` | Restauración del dump en HeatWave probada | — | F4 | P2 | Núcleo |  |
| **R2.3** | `[-] Bloqueado` | Recuperación de web tier por Auto Scaling probada | — | F4 | P2 | Núcleo |  |
| **R2.4** | `[-] Bloqueado` | RTO medido < 5 min en failover de BD | — | F4 | P2 | Núcleo |  |
| **R2.5** | `[-] Bloqueado` | RPO medido < 1 s con dual-write / replicación | — | F4 | P2 | Núcleo |  |


---

<a id="dominio-p---ensayo-técnico-de-sustentación"></a>

## Dominio P: Ensayo técnico de sustentación

<a id="comp-p1"></a>

### Componente P1: Demos del guion (15 min)
- **Fase:** F4 | **Pilar:** — | **Total Tareas:** 8

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **P1.1** | `[-] Bloqueado` | Demo 1: portal por HTTPS con respuesta 200 | — | F4 | — | Núcleo |  |
| **P1.2** | `[-] Bloqueado` | Demo 2: ip route muestra la VPN hacia OCI | — | F4 | — | Núcleo |  |
| **P1.3** | `[-] Bloqueado` | Demo 3: crear incidente → SELECT en OCI | — | F4 | — | Núcleo |  |
| **P1.4** | `[-] Bloqueado` | Demo 4: terminar web-01 → portal sigue → Auto Scaling repone | — | F4 | — | Núcleo |  |
| **P1.5** | `[-] Bloqueado` | Demo 5: Grafana SOC con alarma activa | — | F4 | — | Núcleo |  |
| **P1.6** | `[ ] Pendiente` | Demo 6: Azure WORM rechaza el borrado (409) | — | F4 | — | Núcleo |  |
| **P1.7** | `[-] Bloqueado` | Demo 7: terraform destroy → apply en vivo | — | F4 | — | Núcleo |  |
| **P1.8** | `[-] Bloqueado` | Ensayo completo cronometrado ≤ 15 min | — | F4 | — | Núcleo |  |


<a id="comp-p2"></a>

### Componente P2: Entorno listo para la demo
- **Fase:** F4 | **Pilar:** — | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **P2.1** | `[-] Bloqueado` | Dashboard Grafana precargado con los 6 paneles | — | F4 | — | Núcleo |  |
| **P2.2** | `[ ] Pendiente` | Payloads SQLi/XSS preparados | — | F4 | — | Núcleo |  |
| **P2.3** | `[-] Bloqueado` | Consolas listas (RDS y HeatWave en paralelo) | — | F4 | — | Núcleo |  |
| **P2.4** | `[-] Bloqueado` | Infraestructura levantada tras reinicio de sesión del Lab | — | F4 | — | Núcleo |  |
| **P2.5** | `[-] Bloqueado` | Credenciales del Lab refrescadas en Grafana y Terraform | — | F4 | — | Núcleo |  |


---

<a id="dominio-k---operación-y-control-de-costos"></a>

## Dominio K: Operación y control de costos

<a id="comp-k1"></a>

### Componente K1: Control de presupuesto AWS
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 5

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **K1.1** | `[-] Bloqueado` | AWS Budget con alarma a US$80 | — | F1 | — | Núcleo |  |
| **K1.2** | `[-] Bloqueado` | Revisión periódica de Cost Explorer | — | F1 | — | Núcleo |  |
| **K1.3** | `[-] Bloqueado` | Procedimiento de apagado de EC2/RDS fuera de horario | — | F1 | — | Núcleo |  |
| **K1.4** | `[-] Bloqueado` | VPN Gateway activo solo en la ventana de integración y eliminado después | — | F1 | — | Núcleo |  |
| **K1.5** | `[-] Bloqueado` | Confirmado: no existe NAT Gateway gestionado (se usa NAT Instance) | — | F1 | — | Núcleo |  |


<a id="comp-k2"></a>

### Componente K2: Resiliencia ante cierre de sesión del Lab (4 h)
- **Fase:** F1 | **Pilar:** — | **Total Tareas:** 3

| Código | Estado | Tarea / Elemento Técnico | Detalle / Criterio de Completado | Fase | Pilar | Prioridad | Justificación / Sustento de Evidencia |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **K2.1** | `[-] Bloqueado` | Tras reinicio, web-01/web-02 levantan Nginx solos | — | F1 | — | Núcleo |  |
| **K2.2** | `[-] Bloqueado` | Tras reinicio, app-backend levanta la API sola | — | F1 | — | Núcleo |  |
| **K2.3** | `[-] Bloqueado` | Tras reinicio, los scripts y cron quedan activos | — | F1 | — | Núcleo |  |


---
