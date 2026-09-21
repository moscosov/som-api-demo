# Ciclo completo de Git/GitHub para EA2

**Curso:** CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana
**Experiencia de Aprendizaje:** EA2 — Herramientas disponibles para la colaboración
**Caso práctico:** SOM API Demo — Orden de Servicio (`som_api_demo`)
**Preparado por:** Pablo Moscoso

---

## Contexto

Esta guía documenta el ciclo completo de control de versiones con Git y GitHub — desde la creación del repositorio local hasta su gestión con ramas, pull requests, rebase y cherry-pick — usando como caso práctico el proyecto `som_api_demo` desarrollado para EA2. El anexo oficial del curso (2.4.3) cubre solo los comandos básicos (`config`, `init`, `clone`, `status`, `diff`, `add`, `rm`, `commit`, `push`); esta guía lo extiende con el ciclo colaborativo completo.

Estructura del repositorio de referencia:

```
som_api_demo/
├── som_api_demo.py
├── Dockerfile
├── requirements.txt
├── README.md
├── .gitignore
├── docs/
│   ├── 1_1_EspecificacionFuncional_OrdenServicio_DuocUC.md
│   ├── DisenoFuncional_OrdenServicio_DuocUC.md
│   ├── Contrato_Datos_OrdenServicio_DuocUC.md
│   ├── Contrato_Operativo_OrdenServicio_DuocUC.md
│   ├── GuiaRapida_OrdenServicio_DuocUC.md
│   └── soporte/
│       ├── Validacion_Local_OrdenServicio.md
│       └── Guia_Fundamentos_Docker_OrdenServicio.md
└── postman/
    └── Postman_Coleccion_OrdenServicio_DuocUC.json
```

---

## 1. Repositorio local

```bash
cd som_api_demo/
git init
git config user.name "Pablo Moscoso"
git config user.email "pablo.moscoso@profesor.duoc.cl"
```

`.gitignore` (coherente con lo que genera `som_api_demo.py` — log de eventos y entorno virtual):

```
__pycache__/
*.pyc
.venv/
venv/
.env
*.log
.DS_Store
```

Primer commit, con la estructura completa ya definida (código, Docker, README y toda la jerarquía documental bajo `docs/` y `postman/`):

```bash
git add .
git commit -m "Commit inicial: SOM API Demo - Orden de Servicio (código, Docker, documentación)"
```

**Nota:** el PDF de HPE Claro Ecuador y `Estandar_Documentacion_API_CUY6142.md` quedan fuera del repositorio por decisión editorial — no deben estar en la carpeta antes del `git add`.

---

## 2. Crear el repositorio en GitHub y conectar

Repo vacío en GitHub (sin README/.gitignore/licencia, ya que estos ya existen localmente — evita divergencia de historiales en el primer push):

```bash
git remote add origin https://github.com/<tu-usuario>/som_api_demo.git
git branch -M main
git push -u origin main
```

Nota de autenticación: GitHub requiere Personal Access Token o `gh auth login` para push por HTTPS (el login por password fue eliminado).

---

## 3. Ramas

Ejemplo con una mejora incremental sobre el código ya existente:

```bash
git switch -c feature/mejoras-logging
```

Trabajo sobre `som_api_demo.py` (por ejemplo, enriquecer `registrar()` con el tiempo de respuesta), commit y push:

```bash
git add som_api_demo.py
git commit -m "Agrega duracion de respuesta al log de eventos"
git push -u origin feature/mejoras-logging
```

Ejemplo de rama solo-documentación, para mostrar que el mismo flujo aplica a `docs/`:

```bash
git switch -c docs/actualizar-guia-rapida
# edición de docs/GuiaRapida_OrdenServicio_DuocUC.md
git add docs/GuiaRapida_OrdenServicio_DuocUC.md
git commit -m "Corrige ejemplo de respuesta esperada en Guia Rapida"
git push -u origin docs/actualizar-guia-rapida
```

---

## 4. Pull / sincronización

```bash
git switch main
git pull origin main
git switch feature/mejoras-logging
git merge main
```

---

## 5. Pull Request

Abrir PR de `feature/mejoras-logging` contra `main` en GitHub (web). Con el README ya en el repo, el diff del PR muestra claramente si un cambio de código requiere también actualizar `docs/Contrato_Operativo_OrdenServicio_DuocUC.md` (por ejemplo, si se agrega un nuevo código de error) — punto útil de revisión: ¿el estudiante actualizó el contrato cuando cambió el comportamiento del API?

Tres estrategias de integración al aceptar el PR: *merge commit* (conserva todo el historial), *squash and merge* (un solo commit, historial limpio), *rebase and merge* (historial lineal sin commit de merge).

---

## 6. Rebase

```bash
git switch feature/mejoras-logging
git rebase main
```

Rebase interactivo antes del PR, si hubo varios commits de prueba sobre `som_api_demo.py`:

```bash
git rebase -i HEAD~3
```

**Advertencia pedagógica:** nunca rebasear una rama ya compartida/pusheada sobre la que otros trabajan — reescribe hashes y rompe el historial remoto.

---

## 7. Cherry-pick

Caso realista con esta estructura: se detecta un error en `docs/GuiaRapida_OrdenServicio_DuocUC.md` mientras se trabaja en `feature/mejoras-logging`, pero la corrección debe llegar a `main` de inmediato sin esperar el resto de la rama:

```bash
git log feature/mejoras-logging --oneline
git switch main
git cherry-pick <hash-del-commit-de-la-correccion-en-guia-rapida>
git push origin main
```

---

## 8. Cierre de ciclo

```bash
git push origin main
git branch -d feature/mejoras-logging
git push origin --delete feature/mejoras-logging
git tag -a v1.0 -m "SOM API Demo v1.0 - Orden de Servicio (CUY6142)"
git push origin v1.0
git log --oneline --graph --all
```

El tag `v1.0` es coherente con la versión ya declarada en la Especificación Funcional, los Contratos y la Guía Rápida — refuerza la trazabilidad entre el control de versiones del código y el control de versiones documental que ya manejan las tablas de "Gestión de Versiones" del estándar del curso.

---

## Dificultades probables para estudiantes de sexto semestre sin experiencia previa en Git

- Confundir `git add` faltante antes de `commit` (creen que ya quedó guardado).
- Autenticación HTTPS con token vs. contraseña — punto de fricción casi garantizado.
- Conflictos de merge/rebase: no saben identificar los marcadores `<<<<<<<` / `=======` / `>>>>>>>`.
- Rebasear una rama ya pusheada y generar divergencia con el remoto (necesitarían `--force-with-lease`, riesgoso para enseñar sin resguardos).
- Cherry-pick con conflictos cuando el commit depende de cambios no presentes en la rama destino.

---

*Documento de apoyo docente — complementa el Anexo 2.4.3 (Git y GitHub) del curso CUY6142. No reemplaza el anexo oficial; lo extiende con el ciclo colaborativo completo usando un caso práctico real del curso.*
