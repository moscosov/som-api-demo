# AAY1110 - Evaluación Parcial N° 2: preparador del ambiente

Material de apoyo de la Evaluación Parcial N° 2 (Entrega de encargo) de la asignatura AAY1110 Sistemas Operativos Corporativos en Cloud, Duoc UC, sede Melipilla.

El script `preparar_ambiente_ep2.sh` deja la **instancia B (producción)** con el ambiente de la empresa NuevaNet que se usa en las Fases 3, 4 y 6 de la evaluación. La generación de estos archivos no es parte de lo que se evalúa: es un requisito previo del ambiente.

## Requisitos

- Instancia EC2 con Ubuntu Server 24.04 LTS (instancia B de la evaluación).
- Usuario `ubuntu` con permisos de `sudo`.
- Zona horaria configurada en `America/Santiago` antes de ejecutar el script (Fase 0 del enunciado).

## Uso

Desde el directorio personal del usuario `ubuntu`, con el repositorio ya clonado:

```bash
sudo bash ~/som-api-demo/AAY1110/EP2/preparar_ambiente_ep2.sh
```

Prepara el ambiente completo. Se ejecuta con `sudo` porque escribe en directorios del sistema. Al terminar muestra un listado con fechas de todo lo creado: guárdelo, porque es el estado inicial que se compara en la Fase 4.

```bash
bash ~/som-api-demo/AAY1110/EP2/preparar_ambiente_ep2.sh ayuda
```

Muestra la ayuda del script.

## Qué crea

| Ruta | Contenido |
|---|---|
| `/srv/nuevanet/datos` | Datos de NuevaNet: `clientes.csv`, `ordenes.csv`, `contratos/`, `config/parametros.conf` y `reporte_mensual.dat`. Forma parte del alcance del respaldo. |
| `/var/log/nuevanet` | Siete logs de la aplicación (`app_AAAAMMDD.log`) con 1, 2, 4, 10, 27, 30 y 45 días de antigüedad, entre 2 y 40 MB cada uno. Es el directorio que procesa el script de mantenimiento. |
| `/backups` | Cuatro respaldos antiguos simulados, con 10, 27, 30 y 40 días de antigüedad, cada uno con su archivo `.sha256`. Siguen la convención de nombres de la evaluación (`respaldo_<tipo>_<AAAAMMDD_HHMMSS>.tar.gz`). |

La fecha que aparece en el nombre de cada archivo coincide con su fecha de modificación (`mtime`).

## Comportamiento con el paso de los días

Las antigüedades se calculan desde el momento en que se ejecuta el script. A medida que pasan los días durante el plazo de la evaluación, los archivos envejecen: un log que hoy tiene 2 días tendrá más de 3 días a partir del tercer día, y un respaldo de 27 días superará los 28 días dos días después. Por eso, cada ejecución automática del mantenimiento puede encontrar archivos distintos que comprimir o eliminar. Ese comportamiento es esperado y sirve como evidencia.

## Volver a ejecutar

El script se puede ejecutar nuevamente para reiniciar el ambiente:

- Vuelve a crear `/srv/nuevanet/datos` y `/var/log/nuevanet` desde cero.
- Reemplaza solo los respaldos simulados que él mismo creó, registrados en `/var/lib/nuevanet-ep2/simulados.lst`.
- **No elimina los respaldos reales** generados por el script de respaldo de cada equipo.

Si ya realizó respaldos reales y reinicia el ambiente, los datos de `/srv/nuevanet/datos` cambiarán respecto de esos respaldos. Tenga esto en cuenta antes de la Fase 6 (recuperación).

## Modo actividad (opcional)

```bash
sudo bash ~/som-api-demo/AAY1110/EP2/preparar_ambiente_ep2.sh actividad
```

Simula un día de trabajo de NuevaNet: agrega una orden a `ordenes.csv`, modifica `config/parametros.conf`, crea un archivo de novedad en `contratos/` y genera el log del día en `/var/log/nuevanet`. Sirve para que los respaldos parciales (incrementales o diferenciales) contengan cambios reales que se puedan observar.
