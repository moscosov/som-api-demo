# Estándar de Documentación CUY6142 — MOP, Guías y RCA

**Propósito de este documento:** dejar registrado el estándar aplicado y validado en el MOP y RCA de Rocket.Chat (Actividad 1.3, Semana 3), y en la guía de despliegue y la actividad 2.4.2 (Semana 9), para reutilizarlo en cualquier actividad futura sin tener que reconstruir el criterio desde cero cada vez. Las reglas de la Sección 1 aplican a los MOP, a las Guías Paso a Paso y a las guías de actividad. No es un documento para estudiantes — es de uso interno del docente.

---

## 1. Estándar para MOP (Method of Procedure) y Guías Paso a Paso

### 1.1 Formato general
- Markdown plano (`.md`), sin Notion. Se edita y previsualiza en Typora, se exporta a PDF para distribuir.
- Configuración de exportación a PDF validada (Typora 1.14.9): tema **Github**, papel carta (US Letter, 216 × 279 mm), márgenes superior 5 mm, inferior 5 mm, izquierdo 20 mm y derecho 5 mm. En **Preferencias → Exportar → PDF → Añadir contenido adicional (HTML)** va el CSS de respaldo de la Sección 1.10.
- Encabezado con banner de identificación del curso y del documento, en cita (`>`):

```
> **CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana**
> MOP — Method of Procedure — [Nombre de la actividad], Semana N
```

- Tabla de **Gestión de Versiones** desde la v1.0, con changelog real y específico por versión (no genérico). Ejemplo real:

```
| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.3 | 03/09/2026 | Pablo Moscoso | (1) Paso 10 con variables de pre-provisión de administrador (corrige incidente RCA 00002...); (2) Paso 3 reescrito 100% para PuTTY...; (3) corregido hardcodeo de dominio de ejemplo...
```

### 1.2 Estructura de secciones (numeradas 1–10)

1. Información del Documento (tabla De/Para + Gestión de Versiones)
2. Visión General (qué hace el MOP, qué corrige respecto a guías oficiales/anteriores, qué hallazgos de RCA incorpora)
3. Personal (docente + grupo ejecutor)
4. Acceso al Entorno (plataforma, sección, curso)
5. Pre-requisitos de la Ventana de Mantenimiento
6. Responsabilidades (docente / grupo ejecutor)
7. Datos Dinámicos del MOP (variables a completar antes de ejecutar)
8. Procedimiento (instalación + Pruebas de Servicio + Pruebas Funcionales)
9. Procedimiento de Reversión (Rollback) — con criterio explícito de cuándo se activa
10. Notificación, Aceptación y Escalación

Después de la Sección 10 van los Anexos (ver 1.5).

Las Guías Paso a Paso usan una estructura más corta (Información del Documento, Objetivo, Requisitos Previos, Datos de la Sesión, Procedimiento por Partes, Retomar el Trabajo, Anexos), con las mismas reglas de pasos, placeholders, comandos y anexos de esta sección.

### 1.3 Formato de pasos — bloque, no tabla

Cada paso es un bloque independiente, no una fila de tabla — más legible cuando el estudiante copia y pega:

```
### Paso N — Título del paso

[prosa explicando el paso, contexto, qué hace]

\`\`\`bash
un solo comando
\`\`\`

[resultado esperado, aclaraciones, advertencias, referencias a anexos]
```

Las reglas de los comandos dentro de los pasos están en la Sección 1.10.

### 1.4 Placeholders — regla no negociable

Todo valor que el estudiante debe reemplazar (dominio, IP, credenciales) va **siempre** entre `< >` con nombre descriptivo en mayúsculas, nunca con un valor que parezca real:

- ✅ `<TU_DOMINIO_DUCKDNS>`, `<TU_CONTRASEÑA_ADMIN>`, `<IP_PUBLICA>`
- ❌ Nunca usar un dominio con forma real como ejemplo dentro de un comando ejecutable (ej. `rocket-lab-mop.duckdns.org`) — los estudiantes lo copian tal cual, es el error más frecuente observado.

**Un solo nombre de placeholder por concepto en todo el documento.** No usar `<TU_DOMINIO_DUCKDNS>` en un paso y `<TU_SUBDOMINIO_DUCKDNS>` en otro para lo mismo — genera exactamente la confusión que se busca evitar. Cuando dos documentos se usan juntos (guía de despliegue y guía de actividad), el mismo concepto lleva el mismo placeholder en ambos.

En cada paso donde se ingresa un placeholder, bloque de advertencia **idéntico y repetido** (la repetición exacta es lo que lo hace reconocible):

```
> ⚠️ El dominio de abajo es un EJEMPLO — reemplázalo por el que registraste en DuckDNS (Sección 7).
>
> ❌ Incorrecto: `server_name <mi-grupo-3.duckdns.org>;` (dejaste los símbolos < >)
> ❌ Incorrecto: `server_name rocket-lab-mop.duckdns.org;` (copiaste el ejemplo de otro documento — no es tu dominio)
> ✅ Correcto: `server_name mi-grupo-3.duckdns.org;` (tu dominio real, sin < >)
```

Los ejemplos ❌/✅ de este bloque son la única excepción a la regla de comandos en bloque (Sección 1.10): van en línea, porque muestran la comparación, no se ejecutan.

### 1.5 Anexos — orden fijo

El orden importa pedagógicamente: lo que más se consulta va primero.

1. **Troubleshooting** — primero. Es al que el estudiante recurre cuando algo falla, tiene que estar a mano.
2. **Arquitectura / Notas Conceptuales** — cómo se comunican los componentes entre sí.
3. **Desglose de Comandos** — explicación flag por flag de cada comando nuevo (Docker, o lo que aplique a la tecnología de la actividad). No asumir que `-e VARIABLE="valor"` es autoexplicativo — los estudiantes no asocian el flag con lo que se inyecta al proceso. Cada comando va en su propio bloque de código, seguido de su explicación (no en tabla).
4. **Explicación de Configuración** — línea por línea de cualquier archivo de configuración que el estudiante deba pegar sin entender (nginx, u otro).
5. **Glosario de Términos Técnicos** — último. Es la referencia menos consultada en el momento de ejecutar.

### 1.6 Entradas de Troubleshooting y links de ayuda

Cada entrada del Anexo de Troubleshooting es un título Markdown corto con un número correlativo, seguido del síntoma en negrita y luego la explicación:

```
### Problema N

**Síntoma tal como lo ve el estudiante (mensaje de error)**

Causa y solución, con los comandos en bloque (Sección 1.10).
```

Desde cada paso del Procedimiento que tenga un hallazgo relacionado en Troubleshooting, link con frase **idéntica en todos los casos**, apuntando al identificador del título (minúsculas y guion):

```
👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-n)
```

⚠️ **No usar anclas HTML (`<a id="..."></a>`).** Hasta la v1.1 de la guía de despliegue de la Actividad 2.4.2 se usaban pegadas al texto, pero Typora 1.14.9 las mostró como código visible (observado el 05/10/2026). El título "Problema N" genera el mismo identificador (`problema-n`) en Typora, en el PDF exportado y en la conversión a Word, sin HTML. Por eso el título lleva solo "Problema N": un título largo, con comillas, tildes o signos, genera identificadores distintos según la herramienta.

Se descartó la palabra "solución" en la frase — a veces el anexo solo da una pista o un diagnóstico, no la respuesta exacta, y prometer una solución que no siempre está ahí genera desconfianza. También se descartaron expresiones idiomáticas no usadas en Chile en este contexto (ej. "si te trabaste").

### 1.7 Comandos multilínea

Preferir comandos que quepan en una línea (Sección 1.10): acortar con variables o dividir en varios comandos. Cuando un comando de shell no se puede acortar y se escribe en varias líneas, explicitarlo, porque los estudiantes en general no saben que `\` al final de una línea en bash es continuación de línea:

```
> ⚠️ Todo el bloque de abajo es **un solo comando**, no varios. El carácter `\` al final de cada línea le dice a la terminal "esta línea continúa en la siguiente"... No copies línea por línea: copia el bloque completo de una sola vez.
```

### 1.8 No asumir conocimiento previo

Cada tecnología nueva que aparezca (Docker, nginx, lo que corresponda a la actividad) necesita su propio anexo de desglose — no dar por sentado que el estudiante entiende la sintaxis. Preferir explicar de más que de menos: "es más fácil que sobre explicación a que el estudiante copie y pegue sin entender y luego no sepa diagnosticar su propio error" (criterio del docente, confirmado repetidamente durante esta revisión).

### 1.9 Clientes de conexión — solo lo que realmente usan

Documentar únicamente el cliente que los estudiantes usan en la práctica (ej. PuTTY, no alternativas Linux/`.pem` que nadie usa) — cualquier alternativa no utilizada es ruido, no ayuda. Si un mismo cliente tiene comportamiento distinto entre versiones (ej. PuTTY moviendo la carga de llave privada a un panel "Credentials" desde la versión 0.75), documentar ambas rutas y advertir la diferencia en Pre-requisitos, para revisarlo antes de la sesión, no durante.

### 1.10 Comandos y bloques de código — directriz global

Los estudiantes copian y pegan desde el PDF, muchas veces sin leer, y no siempre saben dónde termina un comando. Reglas:

1. **Todo comando que el estudiante ejecuta o puede copiar va en bloque de código, aunque sea una sola palabra.** Aplica también a los pasos de Troubleshooting, al Desglose de Comandos y a las instrucciones del tipo "repite el comando".
2. **Un comando por bloque.** Si un paso tiene varios comandos, cada uno en su bloque, con una frase antes que diga para qué sirve o "ejecuta estos N comandos, uno a la vez".
3. Las URL que se copian en el navegador o en Postman, y los comandos de la paleta de VS Code (`F1`), van en bloque `text`.
4. Siguen en línea: nombres de archivos, carpetas, campos, valores, teclas, menús, y las menciones de un comando como concepto (ej. "`git push` sube los cambios"), además de los ejemplos ❌/✅ (Sección 1.4).
5. **Largo máximo de 120 caracteres por línea** dentro de un bloque de código. Calibrado el 05/10/2026 con la configuración de la Sección 1.1: en un bloque caben unos 128 caracteres; 120 deja margen. Un comando más largo se acorta (variables, varios comandos) o se divide con `\` según la Sección 1.7. El código Python largo se divide dentro de paréntesis (continuación implícita), nunca con `\`.
6. **Los programas no se copian desde el PDF.** Al copiar desde un PDF se pierde la indentación y un salto de línea visual se pega como salto real. Los programas se publican en el repositorio del curso (`scripts/`) y el estudiante los copia con `cp`. El documento los muestra solo para explicarlos.
7. **CSS de respaldo en la exportación** (Sección 1.1), para que una línea larga que no se copia (por ejemplo, una salida esperada) pase al renglón siguiente en vez de cortarse en el borde de la página:

```html
<style>
pre, .md-fences, .CodeMirror-line { white-space: pre-wrap !important; word-break: break-all; }
</style>
```

### 1.11 Avisos de documentación (evidencias)

Cada paso cuyo resultado el estudiante debe documentar lleva, justo después del resultado esperado, un aviso **idéntico y repetido**, en mayúsculas y con el emoji 📸, seguido de qué debe mostrar la captura:

```
> 📸 **DOCUMENTA ESTE PASO: TOMA UNA CAPTURA DE PANTALLA Y GUÁRDALA COMO EVIDENCIA E1.**
>
> La captura debe mostrar [lo que se revisa en la captura].
```

- Las evidencias se numeran en el orden en que aparecen: `E1`, `E2`... en la guía de actividad, y `D1`, `D2`... en la guía de despliegue.
- La sección de Objetivo o Descripción de cada documento muestra el aviso una vez como ejemplo y explica qué hacer cuando aparece.
- El informe de la actividad incluye todas las evidencias: primero las de la guía de despliegue (sección Preparación del entorno) y luego las de la actividad, con una tabla de evidencia y contenido.

---

## 2. Estándar para RCA (Root Cause Analysis)

### 2.1 Formato general

A diferencia del MOP, el RCA usa HTML embebido en el markdown, con estilo visual institucional (banner DuocUC, colores, tipografías) — es un documento más formal, pensado también para compartir con estudiantes como material de lectura.

```html
<div style="background-color:#307FE2; padding: 28px 36px; margin-bottom: 4px;">
  <img src="[ruta al logo]" alt="Duoc UC" style="height:42px;" />
</div>
<div style="background-color:#1A1A1A; padding: 4px 36px 20px 36px; margin-bottom: 28px;">
  <h1 style="font-family: Merriweather, Georgia, serif; color:#FFFFFF; margin: 12px 0 4px 0;">RCA — Root Cause Analysis</h1>
  <p style="font-family: Lato, Calibri, sans-serif; color:#8BB8E8; margin: 0; font-size: 0.95em;">CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana</p>
</div>
```

Paleta: azul `#307FE2` (encabezados de tabla, títulos), negro `#1A1A1A` (texto principal, banner), gris `#eeeeee` (filas alternadas de tabla). Tipografía: Merriweather/Georgia para títulos, Lato/Calibri para cuerpo.

### 2.2 Estructura de 9 secciones (formato Telefónica)

1. **Identificación RCA** — N° RCA, descripción, sección/curso, docente, estado del RCA (Abierto/Cerrado), fechas, aprobación.
2. **Identificación Incidente** — datos del incidente (fecha, hora, severidad, estado), descripción general, acciones ejecutadas para resolverlo en el momento.
3. **Análisis de Impacto** — a quién afectó, qué servicio, ventana de cambio, downtime.
4. **Causa Raíz** — la explicación técnica real, validada (ver 2.3).
5. **Cronología de Eventos** — tabla fecha/hora/evento, incluyendo el proceso de investigación posterior si hubo una hipótesis inicial descartada.
6. **Acciones Preventivas** — tabla con responsable, descripción, fecha programada, fecha real, estado.
7. **Análisis y Hallazgos** — evidencia (capturas, logs, citas de documentación oficial).
8. **Análisis y Recomendaciones a los Hallazgos** — reflexión de fondo, no solo la corrección puntual (ver ejemplo abajo).
9. **Información Técnica Adicional** — 5 Porqués + definiciones de industria.

### 2.3 Reglas de contenido

**No dejar campos `[a completar]` sin resolver.** Si falta un dato real (fecha, hora, nombre), preguntar directamente antes de cerrar el documento — no rellenar con una suposición no marcada como tal. Si el dato es una estimación, marcarla explícitamente: `~19:30 (estimado — durante la misma sesión, sin registro exacto)`.

**Toda afirmación técnica debe validarse antes de escribirla como definitiva.** Ya ocurrió: una primera hipótesis de causa raíz (que un paso del wizard se podía omitir desde la interfaz) resultó falsa al contrastarla contra la documentación oficial. La corrección quedó documentada en el propio RCA como parte de la Cronología, en vez de borrar el error y pretender que no pasó — es información legítima sobre el proceso de investigación.

**Análisis y Recomendaciones (Sección 8) no es un resumen — es la reflexión de fondo.** Ejemplo real de la profundidad esperada:

> *"La dependencia de servicios cloud externos es un riesgo de diseño, no solo un riesgo de ejecución. [...] Recomendación: al preparar futuras actividades de laboratorio, identificar explícitamente durante la validación previa qué pasos del flujo dependen de servicios externos no controlados por el curso..."*

**5 Porqués — ejemplo real (Anexo 9):**

| N° | Pregunta | Respuesta |
| --- | --- | --- |
| 1 | ¿Por qué los alumnos no pudieron completar el wizard? | Porque quedaron esperando indefinidamente un correo de confirmación que nunca llegó |
| 2 | ¿Por qué no llegó el correo? | Porque ese paso depende del envío de Rocket.Chat Cloud (servicio externo), no de la configuración local del servidor |
| ... | (tantos como sea necesario para llegar a la causa raíz real, no un número fijo) | |

**Definiciones de industria en Sección 9** — glosario ITIL aplicado al contexto académico: Severidad, SLA, Ticket de cambio (RFC), MOP, Rollback, Ventana de Cambio, Downtime, Troubleshooting. Cada una con una nota de cómo aplica (o no aplica, y por qué) al contexto de un laboratorio académico sin SLA real.

**Evidencia con capturas cuando existan**, embebidas con `<img>` (no sintaxis Markdown `![]()` — más frágil cuando se mezcla con HTML denso, puede mostrarse como texto literal en vez de imagen en Typora).

---

## 3. Reglas de trabajo (proceso, no solo el documento)

- **Confirmación explícita antes de crear o modificar cualquier archivo.** Presentar un consolidado de los cambios propuestos y esperar la orden ("adelante", "procede") antes de ejecutar — nunca asumir luz verde de un feedback positivo parcial.
- **Ante cambios grandes o mecánicos** (reordenar anexos, renumerar referencias cruzadas, reemplazos masivos de texto): hacerlo con script y verificación automática (conteo antes/después, diff, balance de bloques de código), nunca a mano — un error de edición manual ya pasó (un `str_replace` mal delimitado borró un encabezado) y se detectó a tiempo solo porque se verificó después de cada cambio.
- **Señalar inconsistencias del propio docente cuando aparezcan** (typos, placeholders duplicados, referencias que no calzan) — no corregir en silencio ni dejarlas pasar sin avisar.
- **Cuando el docente sube una versión editada manualmente**, hacer diff contra la última versión conocida en vez de releer todo el documento de memoria — es más preciso y más rápido para identificar exactamente qué cambió.
- **Entregable final:** archivo `.md` plano, sin Notion, listo para abrir en Typora y exportar a PDF.

---

## 4. Checklist técnico antes de entregar cualquier MOP, guía o RCA

- [ ] Bloques de código balanceados (cantidad de ` ``` ` es par)
- [ ] Sin encabezados duplicados
- [ ] Sin HTML visible en MOP y guías: ni anclas `<a id>` ni otras etiquetas fuera de los bloques de código (el HTML embebido es solo para RCA)
- [ ] Entradas de Troubleshooting como `### Problema N`, numeradas sin saltos
- [ ] Todo link de ayuda (`👉 [...]`) apunta a un `#problema-n` que efectivamente existe
- [ ] Todo comando a ejecutar en bloque de código, uno por bloque, incluido Troubleshooting y Desglose de Comandos
- [ ] Ninguna línea de un bloque de código supera 120 caracteres
- [ ] Avisos 📸 con numeración correlativa, coherente con la tabla de evidencias del informe
- [ ] Sin placeholders huérfanos, duplicados o inconsistentes entre secciones (ni entre documentos que se usan juntos)
- [ ] Si se reordenaron anexos: todas las referencias cruzadas (`Anexo N`, `Anexo N-Letra`, `Problema N`, `Paso N`) actualizadas — verificar con conteo de menciones antes/después, no solo visualmente
- [ ] Sin campos `[a completar]` sin resolver en el RCA
- [ ] Rutas de imágenes: confirmar con el docente si deben ser relativas (documento portable) o absolutas (ya sabe dónde van a vivir los archivos en su equipo)

---

*Documento vivo — actualizar cuando se descubra un criterio nuevo en una futura actividad, en vez de reconstruirlo desde cero cada vez.*
