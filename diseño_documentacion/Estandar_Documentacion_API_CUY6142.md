# Estándar de Documentación API CUY6142

**Propósito de este documento:** dejar registrado el estándar aplicado y validado en los documentos del API demo eTOM/SOM (EA2) — las fichas de Contrato de Datos y Contrato Operativo y de Protocolo, la Especificación Funcional, el Diseño Funcional y la Guía Rápida — para reutilizarlo en cualquier actividad futura que requiera documentar una API, sin reconstruir el criterio desde cero cada vez. Es complementario a `Estandar_Documentacion_CUY6142.md` (que cubre MOP y RCA) — no lo reemplaza ni lo modifica. No es un documento para estudiantes — es de uso interno del docente.

---

## 1. Estándar para Ficha de Contrato (Interface Control Document)

### 1.1 Cuándo usar este formato, y cuándo no

Una Ficha de Contrato documenta **qué es válido** (Contrato de Datos) o **cómo se accede a un servicio** (Contrato Operativo y de Protocolo) — es un documento de referencia, no de procedimiento ni de incidente.

- No usar MOP: MOP documenta un procedimiento paso a paso ejecutable (instalar, configurar, desplegar). Si en el futuro se necesita documentar cómo instalar o desplegar el servicio de una API, eso es un MOP aparte — no se mezcla dentro de la Ficha de Contrato.
- No usar RCA: RCA documenta el post-mortem de un incidente real, con cronología y causa raíz. Un contrato no tiene incidente que analizar.

### 1.2 Formato general

- Markdown plano (`.md`), sin Notion. Se edita y previsualiza en Typora, se exporta a PDF para distribuir.
- Banner HTML institucional embebido, **idéntico en estructura y paleta al usado en RCA** (mismo bloque de código, mismos colores, mismas tipografías) — se reutiliza el branding, no la estructura de secciones de RCA:

```html
<div style="background-color:#307FE2; padding: 28px 36px; margin-bottom: 4px;">
  <img src="[ruta al logo]" alt="Duoc UC" style="height:42px;" />
</div>
<div style="background-color:#1A1A1A; padding: 4px 36px 20px 36px; margin-bottom: 28px;">
  <h1 style="font-family: Merriweather, Georgia, serif; color:#FFFFFF; margin: 12px 0 4px 0;">[Título del documento]</h1>
  <p style="font-family: Lato, Calibri, sans-serif; color:#8BB8E8; margin: 0; font-size: 0.95em;">[Curso]</p>
</div>
```

- Tabla de **Información del Documento** (nombre, versión, fecha, preparado por, curso, actividad relacionada, documento asociado) + tabla de **Gestión de Versiones** desde v1.0 — misma convención que MOP, reutilizada aquí porque ya está validada y resuelve el mismo problema (trazabilidad de cambios).

### 1.3 Regla de separación (no negociable)

Un Contrato de Datos y un Contrato Operativo son **documentos hermanos, siempre en pares, nunca uno solo**:

- El Contrato de Datos nunca incluye endpoints, métodos HTTP, autenticación ni códigos de estado — eso es protocolo.
- El Contrato Operativo nunca redefine la estructura de un recurso (campos, tipos, enums) — eso es dato. Solo lo referencia.

Cada ficha incluye en su tabla de Información del Documento una fila "Documento asociado" apuntando a su par.

### 1.4 Estructura de secciones — Contrato de Datos

1. Información del Documento (tabla + Gestión de Versiones)
2. Propósito y Alcance (qué recurso cubre, qué proceso de negocio simplifica, con qué estándar de industria se alinea conceptualmente — sin reclamar conformidad si no está certificada)
3. Definición del Recurso (tabla de campos: nombre, tipo, obligatoriedad, origen — cliente o servidor, descripción)
4. Reglas de Validación (obligatoriedad, dominios de valores permitidos, campos de solo lectura)
5. Máquina de Estados (si el recurso tiene ciclo de vida — diagrama en texto + tabla de transiciones válidas)
6. Ejemplos de Representación del Recurso (payloads de ejemplo en bloques `json`, nunca código ejecutable)
7. Política de Versionado del Contrato (qué cambio es menor, qué cambio es mayor)
8. Glosario

### 1.5 Estructura de secciones — Contrato Operativo y de Protocolo

1. Información del Documento (tabla + Gestión de Versiones)
2. Propósito y Alcance
3. Modos de Despliegue y Host (todos los perfiles de uso reales, ej. demo en vivo / distribuido, con su host, puerto y cuándo aplica cada uno)
4. Autenticación (mecanismo, alcance de la credencial, momento de validación, código de error si falla)
5. Endpoints y Métodos (tabla método/ruta/acción/éxito/errores) + ejemplos de uso con `curl`, reproducibles también en Postman
6. Formato de Mensajes (content-type, formato de error estandarizado)
7. Códigos de Estado HTTP del Contrato (tabla código/significado en este contrato/cuándo se produce — distinguiendo explícitamente errores de protocolo de errores de contrato de datos, ej. `400` vs `422`)
8. Idempotencia y Concurrencia
9. Exclusiones Declaradas del Contrato (qué queda deliberadamente fuera: persistencia, TLS, gestión de red del entorno — declarado, no omitido en silencio)
10. Control de Versiones del Contrato
11. Glosario

### 1.6 Placeholders en Fichas de Contrato

Mismo criterio de MOP — todo valor que se reemplaza en el momento de uso va entre `< >`, en mayúsculas, con nombre descriptivo (`<IP_DOCENTE>`, `<API_KEY_CUY6142>`).

Diferencia respecto a MOP: **no se usa el bloque de advertencia repetido (`Incorrecto / Correcto`)**. Ese patrón existe en MOP porque el estudiante copia y pega un comando ejecutable de inmediato — el riesgo es dejar el placeholder literal en un comando que sí corre. En una Ficha de Contrato el placeholder aparece en una tabla o un ejemplo de referencia, no en un paso que se ejecuta en el momento de leerlo; basta una nota en prosa indicando de dónde sale el valor real (ej. "el valor real se anuncia al inicio de la sesión").

### 1.7 Ejemplos de protocolo (`curl` / Postman)

Van en el Contrato Operativo, nunca en el de Datos — son ejemplos de invocación, no parte del schema. No reemplazan un MOP: si se necesita documentar la instalación o el despliegue del servicio paso a paso, eso es un MOP independiente.

### 1.8 Convención de nombre de archivo

```
Contrato_<Tipo>_<Recurso>_DuocUC.md
```

Donde `<Tipo>` es `Datos` u `Operativo`, y `<Recurso>` identifica el recurso documentado (ej. `Contrato_Datos_OrdenServicio_DuocUC.md`).

---

## 2. Estándar para Especificación Funcional

### 2.1 Cuándo usar este formato, y cuándo no

Una Especificación Funcional documenta **por qué existe el API y para quién** — contexto de negocio, actores, casos de uso y relación con el proceso que simplifica. No repite el contenido técnico de las Fichas de Contrato; lo referencia.

- No usar si el contenido es técnico (endpoints, schema, códigos de estado): eso ya vive en las Fichas de Contrato — repetirlo aquí duplica trabajo y crea dos fuentes de verdad para lo mismo.
- No usar como sustituto de las Fichas de Contrato: una Especificación Funcional sin sus dos Fichas de Contrato asociadas está incompleta — es el nivel de negocio, no reemplaza el nivel técnico.

### 2.2 Jerarquía documental

```
Especificación Funcional   (qué hace el sistema, para quién, por qué)
        │
        └── Diseño Funcional             (cómo está estructurado para lograrlo)
                │
                ├── Contrato de Datos            (qué es válido)
                └── Contrato Operativo/Protocolo (cómo se accede)
                        │
                        └── Código                (implementación)

Guía Rápida y Colección Postman: documentos de consulta operativa aparte,
para USAR el sistema sin necesitar leer la jerarquía anterior — ver Sección 4.
```

La Especificación Funcional se ubica en el nivel más alto. Un lector debería poder leerla sola y entender el propósito del sistema sin necesitar el Diseño Funcional ni los contratos técnicos.

### 2.3 Formato general

Mismo banner institucional y misma convención de Información del Documento + Gestión de Versiones que la Sección 1.2 — con una adición: la tabla de Información del Documento incluye también una **Lista de Distribución** (quién debe revisar o aprobar el documento, con su rol), y el documento cierra con una sección de **Aprobación** con espacio de firma. Esto no aplica a las Fichas de Contrato (Sección 1), que son de uso interno del docente sin flujo de aprobación formal.

### 2.4 Estructura de secciones

1. Información del Documento (tabla + Lista de Distribución + Gestión de Versiones)
2. Propósito y Contexto de Negocio (qué problema resuelve, en lenguaje de negocio — no técnico)
3. Actores (ver Sección 2.5 — criterio obligatorio de documentación)
4. Definiciones y Abreviaciones (tabla de dos columnas: `Abreviación | Descripción` — no un glosario narrativo)
5. Casos de Uso (ver Sección 2.6 — formato de tabla, no narrativa)
6. Reglas de Negocio (narrativa del ciclo de vida del recurso — la tabla técnica de transiciones vive en el Contrato de Datos, aquí solo se referencia)
7. Relación con el Proceso de Negocio (dónde encaja dentro del estándar de industria de referencia — ej. eTOM — y qué queda deliberadamente fuera)
8. Fuera de Alcance Funcional y Dependencias (qué no resuelve el sistema en términos de negocio, y de qué depende para tener sentido — ej. prerrequisitos del curso, que las Fichas de Contrato asociadas estén vigentes)
9. Lista de Referencias (tabla numerada: documentos del curso relacionados + estándares externos de industria — ver Sección 2.6 sobre por qué esto importa)
10. Control de Versiones de la Especificación
11. Aprobación (firma — ver Sección 2.3)

### 2.5 Actores — criterio de documentación

No asumir que los actores son solo sistemas automatizados. Cuando se conozca que en la operación real del proceso de negocio existe interacción manual directa (soporte técnico, conciliación, validaciones) — no solo el flujo automatizado de punta a punta — esa capa debe documentarse explícitamente como un actor propio, no omitirse ni tratarse como caso especial. Adicionalmente, siempre se documenta el actor pedagógico (estudiante/docente en el ejercicio), señalando explícitamente si replica un rol de negocio real o si es una simplificación exclusiva del curso.

### 2.6 Casos de Uso — formato de tabla, no narrativa

No usar el formato narrativo "Actor, Objetivo, Resultado Esperado". Usar una tabla: `Escenario | Secuencia de llamadas al API | Sección de referencia (Contrato Operativo)`. Cada escenario de negocio se traduce en la secuencia ordenada de llamadas que lo implementan, con referencia cruzada a la sección técnica correspondiente — no se redetalla el endpoint aquí.

Incluir al menos un escenario que solo tenga sentido desde un actor manual/de soporte (Sección 2.5) — por ejemplo, un intento de modificar una orden ya cerrada. Esto ilustra por qué existe una regla de negocio, no solo que existe.

### 2.7 Lista de Referencias — incluir estándares externos

La Lista de Referencias no se limita a documentos internos del curso. Cuando el sistema se alinea conceptualmente con un estándar de industria (ej. eTOM, TMF641), ese estándar se cita explícitamente en esta tabla, con el mismo peso que un documento interno — ancla el trabajo del curso a un marco reconocible fuera de él, no solo a documentos propios.

### 2.8 Placeholders pendientes de dato real

Cuando un campo de la Lista de Distribución o de Aprobación no tiene aún un nombre real asignado (ej. el encargado de línea que debe aprobar), se usa el mismo criterio de placeholder de la Sección 1.6 (`< >`, mayúsculas, nombre descriptivo — ej. `<ENCARGADO_DE_LINEA>`) en vez de dejar el campo vacío o inventar un nombre.

### 2.9 Convención de nombre de archivo

```
EspecificacionFuncional_<Recurso>_DuocUC.md
```

Donde `<Recurso>` identifica el recurso documentado (ej. `EspecificacionFuncional_OrdenServicio_DuocUC.md`).

---

## 3. Estándar para Diseño Funcional

### 3.1 Cuándo usar este formato, y cuándo no

Un Diseño Funcional documenta **cómo está estructurado internamente el sistema para cumplir lo que promete la Especificación Funcional** — arquitectura de componentes, el razonamiento detrás de las decisiones técnicas, y la lógica de procesamiento interna por operación. Se ubica entre la Especificación Funcional y las Fichas de Contrato: no repite el contenido de ninguna de las dos.

- No usar si el contenido es de negocio (actores, casos de uso, alcance): eso ya vive en la Especificación Funcional.
- No usar si el contenido es el contrato exacto de datos o protocolo (campos, endpoints, códigos de estado): eso ya vive en las Fichas de Contrato — aquí solo se referencia.

Precedente de industria que valida esta separación: en un Diseño Funcional real de HPE revisado para este curso, la narrativa de cada operación (ej. "Crear Orden") se documenta como una lista numerada de pasos de validación y lógica interna — sin un solo ejemplo de payload. Los ejemplos concretos de request/response con valores reales viven en la especificación de interfaces técnica, un documento aparte — el mismo criterio que separa nuestro Diseño Funcional de nuestras Fichas de Contrato.

### 3.2 Jerarquía documental

Ver Sección 2.2 — el Diseño Funcional se ubica entre la Especificación Funcional y las Fichas de Contrato.

### 3.3 Formato general

Mismo banner institucional, misma convención de Información del Documento + Lista de Distribución + Gestión de Versiones que la Especificación Funcional (Sección 2.3) — se comparte con estudiantes bajo el mismo criterio.

### 3.4 Estructura de secciones

1. Información del Documento (tabla + Lista de Distribución + Gestión de Versiones)
2. Propósito y Alcance (qué cubre este documento dentro de la jerarquía, qué no repite)
3. Arquitectura de Componentes (diagrama — bloque ```mermaid```, renderiza nativo en Typora — mostrando cliente, capas internas, almacenamiento)
4. Modelo del Proceso (ver Sección 3.5 — narrativa paso a paso por operación, no un diagrama genérico único)
5. Decisiones de Diseño y Alternativas Consideradas (cada decisión técnica con su razón y las alternativas descartadas, no solo la elección final)
6. Manejo de Errores (estrategia de diseño — ej. por qué existe una única fuente de error que alimenta respuesta y log — no la tabla de códigos, que vive en el Contrato Operativo)
7. Restricciones de Diseño (el razonamiento detrás de las exclusiones ya declaradas en el Contrato Operativo, Sección 9 — mismo dato, otro nivel de explicación)
8. Lista de Referencias (mismo criterio que la Especificación Funcional, Sección 2.7)
9. Control de Versiones del Diseño
10. Aprobación (firma)

### 3.5 Modelo del Proceso — narrativa paso a paso por operación

No se documenta como un único diagrama de pipeline genérico para todo el sistema. Por cada operación significativa (ej. crear un recurso, transicionar su estado), se documenta como una lista numerada de los pasos de validación y procesamiento interno — qué se valida primero, qué ocurre si falla, en qué orden se aplican las reglas de negocio. No se repite en este paso a paso la tabla de campos (Contrato de Datos) ni la tabla de códigos de estado (Contrato Operativo) — se referencian por número de sección.

### 3.6 Qué NO debe contener

- Tabla de campos del recurso, valores permitidos, máquina de estados → Contrato de Datos.
- Tabla de endpoints, autenticación, códigos de estado, ejemplos de `curl` → Contrato Operativo.
- Actores, casos de uso de negocio, alcance funcional → Especificación Funcional.

Si alguna de estas categorías aparece redactada dentro del Diseño Funcional, es señal de duplicación — se corrige moviendo el contenido a su documento correspondiente, no copiándolo.

### 3.7 Convención de nombre de archivo

```
DisenoFuncional_<Recurso>_DuocUC.md
```

Donde `<Recurso>` identifica el recurso documentado (ej. `DisenoFuncional_OrdenServicio_DuocUC.md`).

---

## 4. Estándar para Guía Rápida

### 4.1 Cuándo usar este formato, y cuándo no

Una Guía Rápida documenta **cómo operar el sistema sin necesitar entenderlo primero** — es el único documento de este conjunto pensado para copiar y pegar, no para leer. Complementa a los otros cuatro documentos; no los reemplaza y no repite su razonamiento.

- No usar para explicar por qué existe una regla o una decisión: eso es Especificación Funcional o Diseño Funcional — la Guía Rápida no lleva prosa explicativa, solo comando y resultado esperado, con una referencia al documento correspondiente si hace falta explicar algo.
- No usar para definir el contrato completo (todos los campos, todos los códigos de error posibles): eso son las Fichas de Contrato — la Guía Rápida solo cubre el camino feliz de cada operación.
- No es un MOP: no instala ni despliega nada — asume que el servicio ya está corriendo (eso lo cubre el MOP de despliegue).

### 4.2 Formato general

Mismo banner institucional que los demás documentos — pero **sin Lista de Distribución ni sección de Aprobación**: no es un documento de gobernanza sujeto a revisión formal, es una hoja de referencia operativa. Información del Documento se reduce a lo esencial (nombre, versión, fecha, documento asociado) + Gestión de Versiones.

### 4.3 Estructura de secciones

1. Información del Documento (tabla simple + Gestión de Versiones — sin Lista de Distribución ni Aprobación)
2. Valores de Sesión (los placeholders que se completan una sola vez, al principio — host y credencial — nunca repetidos con explicación en cada comando)
3. Flujo Completo (la secuencia de operaciones más común, copiable de principio a fin en un solo bloque conceptual)
4. Comandos por Operación (un bloque `curl` + su respuesta esperada, por cada endpoint del Contrato Operativo)
5. Control de Versiones

### 4.4 Regla de contenido — sin explicar el porqué

Cada entrada es comando + resultado esperado. Si el estudiante necesita entender por qué un comando se comporta así, la guía apunta a la sección correspondiente del Diseño Funcional o de las Fichas de Contrato — no reexplica ahí mismo.

### 4.5 Placeholders — declarados una sola vez

Mismo criterio `< >` de la Sección 1.6, pero a diferencia de las Fichas de Contrato y del MOP, **no se repite la nota de origen en cada comando** — se declaran una única vez en la Sección 2 (Valores de Sesión) y de ahí en adelante se asumen conocidos. Repetir la explicación en cada uno de los comandos rompe el propósito de "copiar y pegar rápido" que define este documento.

### 4.6 Formato de comando y respuesta esperada

```
[bloque bash con el comando curl completo]
[bloque json con la respuesta esperada, abreviada si es necesario]
```

### 4.7 Colección de Postman — artefacto separado, no Markdown

Se entrega además un archivo de **Colección Postman** (formato Postman Collection v2.1, `.json`), importable directamente en Postman. Usa variables de colección (`{{host}}`, `{{api_key}}`) en vez de placeholders `< >` — el estudiante las edita una sola vez en Postman, no en cada request. No sustituye a la Guía Rápida: quien usa `curl` en CLI usa la Guía Rápida; quien usa Postman importa la colección.

Convención de nombre:

```
Postman_Coleccion_<Recurso>_DuocUC.json
```

### 4.8 Convención de nombre de archivo (Guía Rápida)

```
GuiaRapida_<Recurso>_DuocUC.md
```

Donde `<Recurso>` identifica el recurso documentado (ej. `GuiaRapida_OrdenServicio_DuocUC.md`).

---

## 5. Reglas de trabajo (heredadas del estándar general)

- Confirmación explícita antes de crear o modificar cualquier archivo — presentar el diseño y esperar la orden ("adelante", "procede"), igual que en MOP y RCA.
- Señalar inconsistencias del propio docente cuando aparezcan (ej. un endpoint documentado en el Contrato Operativo que no corresponde a ningún campo del Contrato de Datos asociado, un Caso de Uso en la Especificación Funcional sin endpoint que lo respalde, contenido técnico duplicado dentro del Diseño Funcional, o un comando en la Guía Rápida que no coincide con un endpoint del Contrato Operativo).
- Entregable final: archivo `.md` plano, sin Notion, listo para abrir en Typora y exportar a PDF (la Colección Postman es la única excepción — se entrega como `.json`).

---

## 6. Checklist técnico

### 6.1 Ficha de Contrato

- [ ] Banner HTML institucional presente, con la paleta y tipografías correctas
- [ ] Tabla de Información del Documento completa, incluyendo la fila "Documento asociado"
- [ ] Gestión de Versiones desde v1.0
- [ ] Separación estricta respetada: el Contrato de Datos no contiene endpoints/protocolo; el Contrato Operativo no redefine campos del recurso
- [ ] Todo placeholder en formato `< >`, con nota de origen del valor real (sin el bloque de advertencia de MOP)
- [ ] Ejemplos de payload y de `curl` consistentes con los campos y endpoints definidos en ambas fichas
- [ ] Exclusiones del contrato declaradas explícitamente en su propia sección, no omitidas
- [ ] Nombre de archivo sigue la convención `Contrato_<Tipo>_<Recurso>_DuocUC.md`

### 6.2 Especificación Funcional

- [ ] Banner HTML institucional presente
- [ ] Información del Documento completa, incluyendo Lista de Distribución
- [ ] Gestión de Versiones desde v1.0
- [ ] No repite contenido técnico ya cubierto por las Fichas de Contrato (endpoints, códigos de estado, schema) — solo lo referencia
- [ ] Actores documentados reflejan la realidad operativa conocida, no solo el flujo automatizado (Sección 2.5)
- [ ] Casos de Uso en formato de tabla (Sección 2.6), con al menos un escenario desde el actor manual/de soporte
- [ ] Lista de Referencias incluye tanto documentos del curso como estándares externos de industria
- [ ] Sección de Aprobación presente, con placeholder si el nombre real no está definido
- [ ] Nombre de archivo sigue la convención `EspecificacionFuncional_<Recurso>_DuocUC.md`

### 6.3 Diseño Funcional

- [ ] Banner HTML institucional presente
- [ ] Información del Documento completa, incluyendo Lista de Distribución
- [ ] Gestión de Versiones desde v1.0
- [ ] No repite contenido ya cubierto por las Fichas de Contrato o la Especificación Funcional — solo lo referencia (Sección 3.6)
- [ ] Modelo del Proceso documentado como narrativa paso a paso por operación, no como diagrama único genérico (Sección 3.5)
- [ ] Decisiones de Diseño incluyen la razón y las alternativas descartadas, no solo la elección final
- [ ] Sección de Aprobación presente, con placeholder si el nombre real no está definido
- [ ] Nombre de archivo sigue la convención `DisenoFuncional_<Recurso>_DuocUC.md`

### 6.4 Guía Rápida

- [ ] Banner HTML institucional presente
- [ ] Sin Lista de Distribución ni Aprobación (no es documento de gobernanza — Sección 4.2)
- [ ] Valores de sesión (host, credencial) declarados una sola vez, no repetidos por comando (Sección 4.5)
- [ ] Incluye un flujo completo copiable de principio a fin, además de los comandos individuales por operación
- [ ] Cada comando incluye su respuesta esperada
- [ ] Sin prosa explicativa del porqué — solo comando y resultado, con referencia a otro documento si se necesita explicación (Sección 4.4)
- [ ] Cada comando corresponde exactamente a un endpoint vigente en el Contrato Operativo
- [ ] Nombre de archivo sigue la convención `GuiaRapida_<Recurso>_DuocUC.md`
- [ ] Colección de Postman entregada como archivo `.json` aparte, con variables de colección en vez de placeholders `< >` (Sección 4.7)

---

*Documento vivo — actualizar cuando se documente una nueva API en el curso y aparezca un criterio nuevo, en vez de reconstruirlo desde cero cada vez.*
