# 📘 Semana 1 — Guía para Principiantes
## Todo lo que hicimos, explicado comando por comando

**Proyecto:** Production Digital Twin (un simulador de línea de producción)
**Nivel de esta guía:** estudiante que está empezando a programar
**Objetivo:** que entiendas QUÉ hicimos, POR QUÉ, y cómo explicarlo en una entrevista

---

## 🧭 Parte 0: Antes de nada — ¿Qué es la terminal y cómo se lee un comando?

La **terminal** es una ventana donde escribes órdenes de texto en vez de hacer clicks.
El lenguaje que las entiende se llama **bash** (en Mac) o **shell**.

### Anatomía de un comando

```bash
python3 -m pip install pytest
│       │  │   │      └── ARGUMENTO: la cosa sobre la que actúas (pytest)
│       │  │   └── ACCIÓN: qué quieres hacer (install = instalar)
│       │  └── MÓDULO: pip es el "instalador de paquetes" de Python
│       └── FLAG -m: significa "ejecuta este módulo"
└── PROGRAMA: python3 (el intérprete de Python)
```

**Traducción humana:** *"Python, ejecuta tu instalador (pip) y que instale la librería pytest."*

### Los 3 símbolos que verás todo el tiempo

```bash
comando | otro_comando     # El símbolo | se llama PIPE (tubería):
                           # pasa el resultado del primero al segundo

comando > archivo.txt      # El símbolo > significa GUARDAR:
                           # el resultado se escribe en un archivo

comando >> archivo.txt     # Doble >> significa AGREGAR al final:
                           # no borra lo que ya había, añade debajo
```

**Ejemplo real que usamos:**

```bash
python3 -m pip freeze | grep -iE "numpy" > requirements.txt
│                    │ │              │ └── guarda el resultado en requirements.txt
│                    │ │              └── busca solo las líneas que digan "numpy"
│                    │ └── grep = el "buscador" de texto
│                    └── pipe: lo que lista pip freeze entra a grep
└── lista TODAS las librerías instaladas con su versión exacta
```

---

## 🏠 Parte 1: ¿Dónde empezamos? (el punto de partida)

Teníamos un proyecto que **funcionaba solo en mi computadora**:

```
production-digital-twin/
├── main.py            ← el programa principal (el "botón de encendido")
├── src/               ← carpeta con el código del motor
│   ├── simulator.py   ← simula la línea de producción
│   ├── oee.py         ← calcula la eficiencia (OEE)
│   ├── reporter.py    ← genera los reportes (gráficos, Excel)
│   └── ...
├── tests/             ← los exámenes automáticos del código
├── config/            ← la configuración (cuántas máquinas, velocidades)
└── requirements.txt   ← la lista de librerías que necesita
```

### El diagnóstico (en lenguaje humano)

Un "arquitecto de software" (Claude) revisó todo y dijo, básicamente:

> *"Tu código funciona, pero es un juguete, no un producto.
> No anota nada de lo que pasa (no hay bitácora).
> Cuando algo falla, dice 'algo falló' sin decir qué.
> Y tu lista de librerías dice 'un poco de numpy' en vez de 'numpy versión 2.4.6'.
> Ninguna empresa seria compraría esto hoy."*

Esa fue la lista de tareas de la Semana 1.

---

## 🧰 Parte 2: Los 4 conceptos clave, sin tecnicismos

### 1️⃣ Logging = el cuaderno de bitácora

**Antes:** el código usaba `print("haciendo cosas...")`.
El print es un **grito**: se escucha una vez y desaparece.

**Después:** el código usa `logger.info("simulation_started", extra={...})`.
El logger es una **bitácora escrita**: queda registrada con fecha, hora, nivel de importancia y datos extra, en formato JSON (un formato que las computadoras leen solas).

```json
{"timestamp": "2026-09-08T23:45:12+00:00", "level": "INFO",
 "logger": "src.simulator", "message": "simulation_started",
 "context": {"replications": 100, "seed": 42}}
```

### 2️⃣ Excepciones tipadas = alarmas con nombre propio

**Antes:**
```python
try:
    ...
except Exception:      # "algo salió mal" (¿qué? ¿dónde? ¿grave?)
    print("error")
```

**Después:**
```python
except ConfigError:    # "el archivo de configuración está mal"
except SimulationError: # "el motor de simulación falló"
except ReporterError:   # "no se pudo generar un reporte"
```

Cada alarma dice **exactamente qué pasó**, y algunas traen un aviso de
*"esto es recuperable, sigue con lo demás"* (por ejemplo: si falla el
gráfico PNG, igual se generan el Excel y el HTML).

### 3️⃣ CI/CD = el robot examinador

**CI** (Integración Continua) = cada vez que subes código a GitHub,
un robot en la nube:
1. Descarga tu código desde cero (en una computadora limpia)
2. Instala las librerías de tu lista
3. Corre los 32 exámenes (tests)
4. Te pone ✅ verde o ❌ rojo

**Por qué importa:** en tu computadora todo puede funcionar "de casualidad"
porque ya tienes cosas instaladas. El robot empieza de cero, así que
detecta lo que a ti se te esconde. (¡Y esta semana detectó un bug real!)

### 4️⃣ Pin de dependencias = la lista de compras exacta

**Antes:** `numpy>=1.21.0` → *"compra numpy, cualquier versión moderna"*
**Después:** `numpy==2.4.6` → *"compra numpy, exactamente la versión 2.4.6"*

Con `==`, el proyecto se construye **idéntico** en cualquier computadora,
hoy y en dos años. Las industrias reguladas lo exigen.

---

## 💻 Parte 3: Todos los comandos que usamos, comentados

### Bloque 1 — Moverse y mirar

```bash
# Ir a la carpeta del proyecto
# (cd = "change directory" = cambiar de carpeta)
cd ~/Projects/industrial-operations-intelligence/production-digital-twin

# Ver qué hay dentro (ls = "list")
ls -la
#   -l = lista en columnas con detalles
#   -a = muestra también archivos ocultos (los que empiezan con .)

# Crear un archivo de texto con el "mapa" de todas las carpetas
# find = buscador de archivos
#   .            → empieza desde esta carpeta
#   -type f      → solo archivos (no carpetas)
#   -not -path   → excluye estas carpetas (venv, __pycache__, .git)
#   | sort       → ordena alfabéticamente
#   > estructura.txt → guarda el resultado en ese archivo
find . -type f -not -path '*/venv/*' -not -path '*/__pycache__/*' \
     -not -path '*/.git/*' | sort > estructura.txt
```

### Bloque 2 — Preparar el entorno de Python

```bash
# Ver qué versión de Python tienes instalada
python3 --version
# → Python 3.11.9

# Instalar pytest (el programa que corre los exámenes/tests)
# OJO: usamos "python3 -m pip" y no "pip" a secas,
# porque en Mac el comando "pip" solo no siempre existe.
python3 -m pip install pytest

# Instalar TODAS las librerías que el proyecto necesita,
# leyéndolas del archivo requirements.txt
# (el flag -r significa "read from file" = leer de archivo)
python3 -m pip install -r requirements.txt
```

### Bloque 3 — Correr los exámenes (tests)

```bash
# Correr todos los tests en modo verbose (-v = muestra cada test)
# PYTHONPATH=. le dice a Python: "busca módulos también en ESTA carpeta"
# (sin eso, no encuentra la carpeta src/ y da error de import)
PYTHONPATH=. python3 -m pytest tests/ -v

# Resultado esperado:
# ==================== 32 passed in 0.81s ====================
```

### Bloque 4 — Guardar cambios en Git (la máquina del tiempo)

```bash
# 1. Decirle a Git: "toma en cuenta todos los archivos cambiados"
git add .

# 2. Ver el estado: qué está listo para guardarse y qué no
git status

# 3. Guardar una "foto" del proyecto con un mensaje descriptivo
#    (cada foto se llama "commit")
git commit -m "feat(observability): add structured JSON logging"

# 4. Subir la foto a GitHub (la nube)
git push origin main
```

### Bloque 5 — Cuando Git se pone terco (ramas divergidas)

```bash
# Si el push falla con "non-fast-forward", significa:
# "en GitHub hay commits que tú no tienes localmente".
# Primero mira el estado:
git status
# → "Your branch and 'origin/main' have diverged"

# Solución elegante: traer los commits de GitHub y colocar
# los míos ENCIMA de ellos (historial lineal y limpio)
git pull --rebase origin main

# Y ahora sí, subir:
git push origin main
```

### Bloque 6 — Limpiar la casa

```bash
# Crear la carpeta del robot examinador (-p crea carpetas anidadas)
mkdir -p .github/workflows

# Ver si Git está rastreando archivos basura de Mac (.DS_Store)
git ls-files | grep DS_Store
#   git ls-files → lista los archivos que Git vigila
#   | grep ...   → filtra solo los que digan DS_Store

# Agregar una regla al .gitignore para que Git NUNCA vigile .DS_Store
# (>> agrega la línea al final sin borrar lo existente)
echo ".DS_Store" >> .gitignore
```

### Bloque 7 — La lista de compras exacta (pin de dependencias)

```bash
# Generar requirements.txt con versiones EXACTAS (==) en vez de rangos (>=)
#
# Paso a paso del pipe:
#   python3 -m pip freeze  → lista todo lo instalado: "numpy==2.4.6", etc.
#   | grep -iE "^(simpy|numpy|...)"  → filtra solo esas librerías
#        -i = ignorar mayúsculas/minúsculas (¡esto salvó el bug de PyYAML!)
#        -E = permitir el patrón con | como "o esto o aquello"
#        ^  = "que empiece con..."
#   > requirements.txt     → guarda el resultado
python3 -m pip freeze | grep -iE "^(simpy|numpy|pandas|plotly|matplotlib|openpyxl|pyyaml|rich|kaleido|pytest)=" > requirements.txt

# SIEMPRE verifica el resultado después de generar un archivo:
cat requirements.txt
#   cat = muestra el contenido del archivo
#   Deben ser 10 líneas, incluyendo PyYAML==6.0.3
```

### Bloque 8 — Escribir un archivo desde la terminal (heredoc)

```bash
# cat > archivo << 'EOF' ... EOF escribe varias líneas de una vez.
# Todo lo que escribas entre las líneas EOF se guarda en el archivo.
cat > .github/workflows/tests.yml << 'EOF'
name: Tests
on:
  push:
    branches: [ main ]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest tests/ -v
        env:
          PYTHONPATH: .
EOF
```

### Bloque 9 — Apuntar al nombre correcto del repo

```bash
# Cambiar la dirección remota (después de renombrar el repo en GitHub)
git remote set-url origin https://github.com/icqdgonzalezs/production-digital-twin.git

# Verificar que quedó bien (debe mostrar la URL nueva dos veces)
git remote -v
```

---

## 🕵️ Parte 4: Los 3 bugs de la semana (historias de detective)

### Bug 1 — "pip: command not found"
- **Pista:** la terminal no reconocía `pip`.
- **Causa:** en Mac, `pip` no está en el PATH (la lista de programas que la terminal conoce).
- **Solución:** `python3 -m pip ...` (invocar el módulo desde Python).
- **Lección:** si un comando no existe, prueba invocarlo como módulo con `-m`.

### Bug 2 — "rejected: non-fast-forward"
- **Pista:** el push fue rechazado; `git status` decía "diverged".
- **Causa:** había 6 commits en GitHub que mi copia local no tenía.
- **Solución:** `git pull --rebase origin main` y luego push.
- **Lección:** antes de subir, asegúrate de tener lo último del remoto.

### Bug 3 — El robot examinador en rojo: "No module named 'yaml'"
- **Pista:** 32 tests verdes en mi Mac, pero CI rojo con 21 tests.
- **Causa:** la librería se instala como **PyYAML** (con mayúsculas) pero se
  importa como **yaml**. Mi filtro `grep` buscaba "pyyaml" en minúsculas y
  la dejó fuera del requirements.txt. Mi Mac no lo notó porque ya la tenía
  instalada; la computadora limpia del CI, sí.
- **Solución:** regenerar la lista con `grep -i` (insensible a mayúsculas).
- **Lección triple:**
  1. Nombre de paquete ≠ nombre de import (PyYAML/yaml, Pillow/PIL).
  2. Tu computadora puede esconder bugs: el entorno limpio del CI los revela.
  3. Siempre revisa el archivo que generaste (`cat requirements.txt`).

---

## 🐍 Parte 5: El código Python que creamos (visto por encima)

### `src/logging_config.py` — la bitácora
Dos piezas:
- `JSONFormatter`: convierte cada mensaje en una línea JSON.
- `get_logger("nombre")`: te entrega un cuaderno listo para escribir.

### `src/exceptions.py` — el árbol de alarmas
```
ProjectError          ← la alarma madre (código 1000)
├── ConfigError       ← 1100: configuración mal
├── ValidationError   ← 1200: datos de entrada mal
├── SimulationError   ← 1300: falló la simulación
├── ReporterError     ← 1400: falló un reporte (+ aviso "recuperable")
└── AuthenticationError ← 1500: reservada para el futuro login
```

### El refactor de `reporter.py`
Una función gigante de 200 líneas que hacía 5 trabajos
se dividió en ~15 funciones pequeñas, cada una con un solo trabajo.
(Regla de oro: **una función, una responsabilidad**.)

---

## 💼 Parte 6: Cómo contarlo en una entrevista (con tus palabras)

### El guion de 60 segundos

> "Tenía un simulador de producción en Python que funcionaba solo en mi
> computadora. Lo llevé a estándares de producto: le agregué logging
> estructurado en JSON para observabilidad, una jerarquía de excepciones
> tipadas con códigos de error, refactoricé una función de 200 líneas en
> funciones de responsabilidad única, y sumé 21 tests nuevos para llegar a 32.
> Arreglé el pipeline de CI que no resolvía los imports, y pineé las
> dependencias para builds reproducibles. El CI me atrapó un bug real:
> una librería que faltaba porque su nombre de paquete (PyYAML) difiere del
> nombre de import (yaml). Lo resolví y dejé el pipeline en verde."

### Preguntas que te pueden hacer (y respuestas simples)

**¿Por qué logging y no print?**
→ El print se pierde al cerrar la terminal. El log queda registrado con
fecha, nivel y datos, y los sistemas de monitoreo lo leen automáticamente.

**¿Por qué excepciones con tipos propios?**
→ Para que quien recibe el error sepa QUÉ falló y decida: reintentar,
abortar o continuar. Un `except Exception` genérico lo convierte todo
en el mismo misterio.

**¿Qué es CI y para qué te sirvió?**
→ Un robot que corre mis tests en una computadora limpia cada vez que subo
código. Me sirvió para descubrir un bug que mi computadora ocultaba.

**¿Por qué versiones exactas en requirements.txt?**
→ Para que el proyecto se instale idéntico en cualquier máquina. Con rangos
abiertos, una librería nueva puede romper todo sin que tú cambies nada.

**¿Qué es rebase y cuándo lo usaste?**
→ Una forma de integrar cambios remotos colocando mis commits encima,
dejando el historial lineal. Lo usé cuando mi push fue rechazado por
ramas divergidas.

---

## 📖 Parte 7: Glosario del principiante

| Palabra | Qué significa en criollo |
|---|---|
| Terminal / bash | La ventana de comandos de texto |
| Flag | Una opcionsita con guion: `-v`, `-r`, `-m` |
| Pipe ( \| ) | Pasar el resultado de un comando al siguiente |
| Redirección ( > ) | Guardar el resultado en un archivo |
| Commit | Una "foto" guardada del proyecto |
| Push | Subir tus fotos a GitHub |
| Pull / rebase | Bajar los cambios de otros y acomodar los tuyos encima |
| PATH | La lista de programas que la terminal conoce por nombre |
| Entorno limpio | Una computadora sin nada instalado de antes (como el CI) |
| Test | Un examen automático que verifica que el código hace lo correcto |
| CI/CD | El robot que construye y examina tu código solo |
| JSON | Formato de texto ordenado que las máquinas leen fácil |
| OEE | Medida de eficiencia de una máquina: disponibilidad × rendimiento × calidad |

---

## 📊 Parte 8: Los números de la semana

| Cosa | Antes | Después |
|---|---|---|
| Tests | 11 | 32 |
| Prints sueltos | ~15 | 0 |
| Errores "genéricos" | 1 | 0 |
| Función más larga | 200 líneas | <40 líneas |
| Lista de librerías | "más o menos" (>=) | exacta (==) |
| CI | roto | verde ✅ |

---

## 🚀 Parte 9: Lo que sigue (Semana 2)

Convertir el simulador en un **servicio web** (API) con FastAPI:
que otra computadora pueda pedirle una simulación por internet y recibir
los resultados. Eso es lo que lo vuelve un producto vendible.

---

*Guía escrita para mi yo del futuro y para cualquier estudiante que empiece.
Semana 1: de script a producto con cimientos.*
