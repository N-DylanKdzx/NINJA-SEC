# NINJA-SEC · Lo que falta antes de AWS

Contexto al 12 de noviembre de 2026. Los estados y las evidencias se mantienen en el [checklist técnico](NINJA-SEC_Avance_Tecnico.md).

## Grafana en OCI · B9.7, B9.13, M9.2, M9.3 y T2.3

- **M9.2 ya está completada.** Grafana consultó métricas de CPU de OCI y mostró conexiones MySQL. La evidencia está en B9.6 y B9.10.
- **B9.7, B9.13, M9.3 y T2.3 siguen bloqueadas.** La prueba de Azure Automation exportó 100 eventos únicos de `ninjasec-law` a un bucket privado de OCI. Se verificó el SHA-256 y quedó habilitada la exportación diaria a las 03:00 de Colombia. La alternativa acordada para B9.7 es leer ese archivo exportado desde Grafana. El lector está en el repositorio, pero los intentos de SSH a la VM por Bastion agotaron el tiempo de espera y Run Command quedó en `ACCEPTED`.
- **Siguiente paso.** Recuperar el acceso a `bastion-utility-01`, instalar el lector con la identidad de instancia de OCI y configurar el datasource alternativo y el panel 6. Comparar al menos un `EventId` del panel con el archivo exportado y verificar que la configuración del datasource queda libre de credenciales en Git. Registrar en B9.7 que se usó la alternativa de exportación.

## Azure WORM · P1.6

- **Pendiente como demo.** En M8.3 ya se verificó que Azure rechazó el borrado de un blob de auditoría con HTTP `409 BlobImmutableDueToPolicy`.
- **Siguiente paso.** Reproducir la prueba en el entorno de demostración con un blob de prueba protegido y guardar la respuesta `409` como evidencia de P1.6. Este bloque se puede hacer mientras se recupera el acceso a OCI.

## Portal standby y respaldo diario · M5.1 y M6.1

- **M5.1 está bloqueada.** El balanceador de OCI figuraba como `CRITICAL` en la última comprobación registrada. Verificar el servicio del portal en la VM, recuperar el estado saludable del backend y probar el portal a través del balanceador de OCI.
- **M6.1 está pendiente.** Ya se verificaron una copia puntual del respaldo de HeatWave a Azure WORM y una restauración aislada en HeatWave. Falta instalar el `cron` diario de `mysqldump` en el host autorizado y confirmar que una ejecución programada produce un archivo válido en el bucket privado de respaldos de OCI. La copia de prueba a Azure se hizo manualmente.

## Cloudflare y dominio · G1.5, G1.6, D1.1 y D1.3

- **G1.5, G1.6 y D1.1 están pendientes.** Verificar o crear la cuenta Cloudflare Free, usar un dominio bajo nuestro control y delegarlo mediante sus servidores DNS. Confirmar que la zona queda activa.
- **D1.3 está bloqueada.** Con la zona activa y el balanceador de OCI saludable, crear y verificar el registro secundario hacia OCI. El registro primario y la prueba de conmutación quedan para la integración posterior.

**Orden acordado.** Completar primero estos bloques. P1.6 y la preparación de Cloudflare pueden avanzar en paralelo a la recuperación de la VM. Después sigue AWS, que continúa siendo obligatorio para la entrega y para las pruebas de integración multinube.
