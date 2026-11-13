# NINJA-SEC · Ubicación de credenciales y accesos

Referencia verificada el 12 de noviembre de 2026 para retomar el proyecto desde otro chat. Las rutas de Windows corresponden al equipo de Dylan. Este inventario contiene referencias de ubicación y uso. Los valores se conservan en Windows o en los servicios indicados.

## Equipo Windows

| Elemento | Ruta | Para qué sirve |
| --- | --- | --- |
| Clave privada de firma OCI | `C:\Users\DYLAN\.oci\ninjasec-terraform\api_key.pem` | Terraform y OCI CLI la usan para autenticarse ante OCI mediante el perfil `NINJA_SEC_TERRAFORM`. |
| Configuración de OCI CLI | `C:\Users\DYLAN\.oci\config` | Define los perfiles de OCI y las referencias a sus archivos de autenticación. |
| Llave privada de OCI Bastion | `C:\Users\DYLAN\.ssh\ninjasec_oci_bastion_rsa` | Autentica el tramo SSH hacia el servicio OCI Bastion. |
| Llave privada de las VM OCI | `C:\Users\DYLAN\.ssh\ninjasec_oci_ed25519` | Autentica el acceso SSH al usuario de la VM privada a través de Bastion. |
| Huellas SSH de OCI | `C:\Users\DYLAN\.ssh\ninjasec_oci_known_hosts` | Permite verificar la identidad del servidor SSH. Contiene huellas de servidor. |
| Credencial de administración MySQL | `C:\Users\DYLAN\.oci\ninjasec-mysql-admin.dpapi` | Acceso administrativo a HeatWave. Se usó para la prueba de restauración aislada. |
| Credenciales de aplicación MySQL | `C:\Users\DYLAN\.oci\ninjasec-mysql-app.dpapi` y `C:\Users\DYLAN\.oci\ninjasec-mysql-portal.dpapi` | Copias locales protegidas por Windows para los accesos de aplicación y portal. El servicio desplegado consulta OCI Vault. |
| Sesiones OCI CLI | `C:\Users\DYLAN\.oci\sessions\` | Subcarpetas `NINJA_SEC`, `NINJA_SEC_B4`, `NINJA_SEC_MON`, `NINJA_SEC_TF` y `NINJA_SEC_VAULT`. Cada una contiene un archivo `token` y su par de claves de sesión. Su vigencia queda por verificar al reutilizarlas. |
| Sesión Azure CLI | `C:\Users\DYLAN\.azure\msal_token_cache.bin` | Caché de inicio de sesión de Azure CLI. Si la sesión caduca, se renueva iniciando sesión con la cuenta de Azure correspondiente. |

Los archivos `.dpapi` dependen de la protección de Windows del usuario que los creó. En otro equipo o cuenta hay que comprobar que se pueden recuperar antes de confiar en una copia.

### Inicio de sesión en el portal NINJA-SEC (OCI)

- Carpeta local: C:\Users\DYLAN\AppData\Local\NINJA-SEC\Credenciales
- Archivo: portal-oci.credential.clixml. Contiene el usuario del portal y la contraseña cifrada mediante DPAPI de Windows. Se abre con la cuenta de Windows que guardó el archivo en este equipo.

Al crear, recuperar o rotar una credencial de NINJA-SEC que el titular necesite usar, guardar una copia cifrada en esta carpeta y comprobar que su cuenta de Windows puede abrirla. Si una credencial ya se administra en un almacén de secretos y no requiere una copia local, registrar dónde se administra. En Git registrar únicamente la ubicación, el propósito y cómo recuperar el acceso.


## OCI y Azure

| Ubicación | Qué guarda o autoriza |
| --- | --- |
| **OCI Vault → secreto de MySQL HeatWave** | Credencial de aplicación que consumen el portal y el exportador MySQL. La configuración en `bastion-utility-01` referencia el secreto mediante `DB_SECRET_OCID`; la VM lo lee con su identidad de instancia. El identificador y la prueba están en **B6.2–B6.3** del checklist. |
| **Azure Automation → `ninjasec-oci-audit` → Variables → `OciAuditReader`** | Variable cifrada con la credencial de OCI usada por los runbooks. Permite leer OCI Audit y escribir el objeto `latest.json` del bucket privado `ninjasec-grafana-azure-logs`. |
| **Azure Automation → `ninjasec-oci-audit` → Identidad** | Identidad administrada que obtiene tokens durante la ejecución. Los runbooks la usan para escribir el archivo de auditoría en Azure, enviar eventos a Log Analytics y consultar `ninjasec-law` para exportarlos a OCI. |
| **Grafana → fuentes de OCI y de eventos exportados** | El datasource OCI usa identidad de instancia. El lector alternativo de eventos Azure está preparado para usar esa misma modalidad y queda pendiente de despliegue. Microsoft Entra rechazó el registro de la aplicación del datasource nativo y por eso no se generó un `client_secret` para Grafana. |

Para retomar el trabajo, usa el [checklist técnico](NINJA-SEC_Avance_Tecnico.md) para comprobar el estado vigente y las evidencias.
