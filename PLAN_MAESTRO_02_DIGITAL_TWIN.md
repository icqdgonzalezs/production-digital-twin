# 🏭 Production Digital Twin
## Plan maestro de construcción: simulación de eventos discretos, ingeniería de producción y análisis de capacidad

> **Documento maestro de construcción, aprendizaje y evolución del proyecto.**
>
> Este archivo define la arquitectura, el modelo industrial, el alcance funcional, la metodología estadística, la estructura de software, la estrategia de testing, el flujo de trabajo de terminal/Bash, el roadmap y los criterios de calidad que utilizaremos para construir **Production Digital Twin** desde su estado actual hasta una versión de portafolio de alto impacto, al mismo estándar que *Industrial KPI Intelligence*.

---

# 0. Propósito de este documento

Este archivo será utilizado simultáneamente como:

1. Especificación funcional.
2. Especificación técnica.
3. Bitácora de construcción.
4. Guía de aprendizaje.
5. Guía de terminal/Bash y Python.
6. Guía de simulación de eventos discretos y estadística de salida.
7. Guía de pruebas y calidad de software.
8. Lista de verificación de lanzamiento para GitHub.
9. Material de preparación para entrevistas técnicas.

La regla general será:

> **No implementaremos una funcionalidad solamente porque se ve bien.**
>
> Cada componente deberá responder a un problema operativo o de capacidad y deberá poder defenderse técnicamente.

---

# 1. 🎯 Visión definitiva del proyecto

## 1.1 Qué estamos construyendo

**Production Digital Twin** será un gemelo digital interactivo de una línea de envasado para:

- simular el comportamiento dinámico de la línea (eventos discretos);
- evaluar capacidad instalada bajo variabilidad y fallas;
- predecir OEE con intervalos de confianza;
- detectar y rankear cuellos de botella;
- analizar utilización, WIP, blocking y starvation;
- evaluar capacidad de proceso (Cp/Cpk) de tiempos de ciclo;
- comparar escenarios What-If (buffers, velocidad, mantenimiento, CAPEX);
- estimar pérdidas operativas;
- generar reportes ejecutivos profesionales;
- apoyar decisiones de mejora continua e inversión.

No será presentado como un sistema de control de planta.

No enviará comandos a PLC.

No reemplazará MES, SCADA, ERP ni planificadores.

Su rol será:

> **Soporte para la toma de decisiones / Análisis de capacidad y desempeño**

---

# 2. 🏭 Dominio industrial elegido

## 2.1 Industria

El proyecto estará basado en una:

> **Línea sintética de envasado de alimentos sólidos (filling–sealing–packing).**

La línea será sintética, pero inspirada en procesos de envasado reales.

Importante:

- no diremos que reproduce una planta real específica;
- no utilizaremos datos internos de ninguna empresa;
- usaremos maquinaria y problemas industriales plausibles;
- las reglas del modelo (distribuciones, fallas, buffers) serán explícitamente documentadas.

La inspiración de dominio permite que el modelo responda preguntas que un ingeniero de producción, mantenimiento o mejora continua podría realmente realizar.

---

# 3. 🏗️ Modelo físico de la línea

## 3.1 Estructura general

```text
LÍNEA DE ENVASADO DE SÓLIDOS
│
├── Alimentador de envases
├── Llenadora (S01)
├── [Buffer B1]
├── Selladora (S02)
├── [Buffer B2]
├── Etiquetadora (S03)
├── [Buffer B3]
├── Báscula de control (S04)
├── Detector de metales (S05)
├── Empaquetadora de cajas (S06)
└── Paletizador (S07)
```

La línea no será perfectamente balanceada: una estación puede ser más lenta o más fallera que otra. Esto es intencionalmente más realista que obligar a todas las estaciones a tener la misma tasa.

## 3.2 Buffers

Los buffers finitos son ciudadanos de primera clase del modelo:

```text
buffer_capacity = 0   → línea sincronizada (blocking/starvation máximos)
buffer_capacity = N   → desacople parcial
buffer_capacity = ∞   → desacople total (caso de comparación, no default)
```

---

# 4. 🔢 Cantidad de equipos

Modelo objetivo inicial:

- 7–9 estaciones modeladas
- 6–8 buffers intermedios
- 3–4 estaciones críticas para análisis profundo

Esto evita confundir:

```text
cantidad de estaciones modeladas
```

con:

```text
cantidad de estaciones analizadas con máxima profundidad
```

El gemelo deberá ser capaz de representar una línea mayor de lo que necesariamente se muestra en el primer vistazo.

---

# 5. 🚨 Estaciones críticas

Las Critical Stations serán las que concentren:

- menor tasa nominal (candidatas a cuello de botella);
- mayor variabilidad de ciclo;
- peor combinación MTBF/MTTR;
- mayor impacto en OEE.

Ejemplo conceptual:

```text
S01-LLEN-01   (llenadora, alta utilización)
S02-SELL-01   (selladora, fallas frecuentes)
S06-PACK-01   (empaquetadora, variabilidad alta)
```

La selección exacta se definirá al cerrar el modelo de configuración.

---

# 6. 🆔 Identificación de estaciones

No eliminaremos los ID técnicos.

Utilizaremos varios atributos.

## ID de estación

```text
S02-SELL-01
```

Interpretación:

```text
S02 → posición secuencial en flujo
SELL → tipo de estación
01 → número secuencial
```

## Nombre de estación

```text
Selladora 01
```

## Tipo de estación

```text
SELLADO
```

## Ejemplo completo

```text
id_estacion   = S02-SELL-01
nombre        = Selladora 01
tipo          = SELLADO
upstream      = S01-LLEN-01
downstream    = S03-ETIQ-01
buffer_up     = B1
buffer_down   = B2
```

Esto permite separar:

- identidad;
- descripción;
- clasificación;
- ubicación en el flujo.

---

# 7. 🧱 Jerarquía industrial

La jerarquía conceptual será:

```text
PLANTA
  ↓
LÍNEA
  ↓
ESTACIÓN
  ↓
VARIABLE (ciclo, estado, calidad)
```

Los buffers se modelan como entidades de conexión entre estaciones, no como estaciones.

Esta jerarquía será la base para el *drill-down* del dashboard.

---

# 8. 🎲 Modelo de simulación

El conjunto de experimentos no se limitará a una corrida.

Objetivo de simulación:

- horizonte por réplica: 480 min (1 turno);
- warmup: 30 min (excluido de KPIs);
- réplicas Monte Carlo: 100 (rango aceptado 30–200);
- estaciones: 7–9;
- buffers finitos;
- fallas aleatorias (MTBF/MTTR);
- variabilidad de ciclo por estación.

Criterio de suficiencia estadística:

```text
semiancho del IC del OEE ≤ ±2 puntos
→ si no se cumple, aumentar réplicas (documentado)
```

El número exacto de réplicas se definirá en función de precisión, rendimiento y simplicidad.

---

# 9. 🕒 Tiempo

Campos esperados por réplica:

```text
replica_id
seed
duración_simulada
warmup
tiempo_productivo
tiempos_de_pérdida (fallas, blocking, starvation, cambios)
```

Reglas:

- el reloj es simulado (minutos), no tiempo real;
- los KPIs se calculan solo sobre el horizonte post-warmup;
- cada reporte mostrará timestamp real de generación.

---

# 10. 👥 Turnos y operadores

En V1 los turnos no se modelan como entidades, sino como **escenarios de variabilidad**:

```text
Escenario base      → variabilidad estándar
Escenario noche     → cycle_time_std mayor
Escenario mejorado  → MTTR menor (mantenimiento optimizado)
```

No agreguemos atributos de personas. La finalidad es estudiar desempeño operacional, no construir un sistema de RRHH.

---

# 11. 📦 Productos y lotes

Productos:

```text
PRD-A   PRD-B   PRD-C
```

Cada producto podrá tener:

- tasas nominales por estación;
- variabilidad propia;
- tasa de calidad propia.

Lotes derivados:

```text
LOTE-000001 ...
```

El lote permitirá trazabilidad de producción en reportes y análisis de variabilidad entre lotes.

---

# 12. 🧪 Variables estocásticas por tipo de estación

Las distribuciones serán específicas de cada tipo de estación.

### Llenadora

```text
cycle_time ~ Normal(mu, sigma)     # mu = 1/rate_upm
fallas ~ Exp(MTBF), reparación ~ Exp(MTTR)
quality_rate ~ Beta(a, b)
```

### Selladora

```text
mayor probabilidad de falla (MTBF menor)
```

### Báscula / Detector

```text
alta confiabilidad, ciclos rápidos, rechazo por calidad
```

Esto evita el error de usar exactamente los mismos parámetros para todas las máquinas.

---

# 13. 🛠️ Calidad, defectos, scrap y reproceso

Por estación:

```text
unidades_procesadas
unidades_defectuosas
quality_rate
```

La calidad final de línea será el resultado compuesto del flujo (una unidad defectuosa en cualquier estación afecta el Q del OEE).

Cuando corresponda, deberá cumplirse:

```text
unidades_buenas + unidades_defectuosas = unidades_procesadas
```

---

# 14. 🎲 Motor de simulación

`src/simulator.py` deberá:

- ejecutar eventos discretos con SimPy;
- modelar blocking y starvation con buffers finitos;
- generar fallas y reparaciones;
- acumular métricas por estación y por réplica;
- mantener reproducibilidad;
- permitir modificar supuestos mediante configuración YAML.

La simulación no debe ser ruido aleatorio sin estructura: debe respetar conservación de flujo.

Invariantes obligatorias:

```text
iniciadas = terminadas + WIP_final
producidas ≤ capacidad_teórica × tiempo_disponible
```

---

# 15. 🌱 Reproducibilidad

Se mantendrá una semilla base fija:

```python
SEMILLA_BASE = 42
seed_réplica_i = SEMILLA_BASE + i
```

La idea:

```text
misma semilla
    ↓
misma secuencia aleatoria
    ↓
mismos resultados de simulación
```

Esto permite reproducir:

- bugs;
- pruebas;
- comparaciones entre escenarios y versiones.

---

# 16. 🎭 Eventos de proceso simulados

## Falla aleatoria

```text
S02-SELL-01
    ↓
ocurre falla (Exp MTBF)
    ↓
estación DOWN (Exp MTTR)
    ↓
upstream se bloquea / downstream se hambruna
```

## Variabilidad de ciclo

```text
ciclo real = ciclo nominal × (1 + ruido)
```

## Efecto de escenario

```text
Escenario noche
   ↓
mayor variabilidad
   ↓
menor throughput efectivo
```

## Interacción con buffer

```text
buffer pequeño
   ↓
propagación de paradas
   ↓
pérdida de throughput
```

Estas señales serán diseñadas para que el gemelo pueda descubrir patrones, pero serán explícitamente sintéticas.

---

# 17. 📋 Límites de especificación

Cada estación crítica tendrá configuración de capacidad:

```yaml
ciclo_s02:
  nominal: 0.68        # segundos/unidad
  lsl: 0.60
  usl: 0.80
```

Los límites:

```text
LSL
USL
```

son **límites de especificación** de tiempo de ciclo.

No son lo mismo que los límites de control.

---

# 18. 📈 Límites de control aplicados a salida

En el gemelo, los "límites de control" se aplican al **análisis de salida**:

```text
IC 95% del OEE
IC 95% del throughput
```

Regla fundamental:

```text
Límites de especificación (ciclo)
≠
Intervalos de confianza (salida Monte Carlo)
```

El dashboard deberá hacer visible esta diferencia.

---

# 19.  Estadística de salida (output analysis)

La primera versión debe:

- calcular media y desviación entre réplicas;
- construir IC 95% (t-Student);
- reportar semiancho relativo;
- mostrar histogramas y violines;
- declarar si la precisión es suficiente.

---

# 20. 📊 Selección de gráficos

No elegiremos un gráfico por estética.

## Distribución de réplicas

```text
violín / boxplot de OEE y throughput
```

## Capacidad

```text
histograma de ciclos + LSL/USL
```

## Cuellos de botella

```text
mapa de calor de utilización / blocking / starvation
```

## Pérdidas

```text
Pareto de tiempos de pérdida
```

La visualización debe ayudar a decidir, no convertirse en decoración.

---

# 21. 🚨 Estados de desempeño

Estados de capacidad:

```text
CAPAZ (Cpk ≥ 1.33)
MONITOR (1.00 ≤ Cpk < 1.33)
NO CAPAZ (Cpk < 1.00)
```

Estados de estación:

```text
CUELLO DE BOTELLA
VIGILAR
NORMAL
```

---

# 22. 📐 Análisis de capacidad

El motor calculará por estación:

```text
media
sigma
Cp
Cpk
n
LSL
USL
clasificación
```

## Cp

```text
Cp = (USL - LSL) / (6 × sigma)
```

## Cpk

```text
Cpk =
mínimo(
    (USL - media) / (3 × sigma),
    (media - LSL) / (3 × sigma)
)
```

---

# 23. ⚠️ Interpretación de capacidad

Convención del proyecto:

```text
Cpk >= 1.33  → Capaz
1.00 <= Cpk < 1.33 → Marginal / Monitor
Cpk < 1.00 → No capaz / Acción requerida
```

Estas categorías son una convención de informes del proyecto y no deben presentarse como ley universal.

Además:

> **Cp/Cpk no demuestra por sí solo que el proceso está estable.**

La interpretación deberá considerar estabilidad, distribución, tamaño muestral y calidad de la configuración.

---

# 24. 📊 Motor de KPI

Indicadores clave:

```text
OEE = A × P × Q        (ISO 22400)
Disponibilidad (A)
Rendimiento (P)
Calidad (Q)
Throughput (u/min efectivas)
Utilización por estación
WIP promedio
MTBF / MTTR observados
```

No calcularemos OEE si faltan los componentes necesarios; el gate lo impedirá.

---

# 25. 🧮 Agregación correcta

No promediaremos ratios sin analizar volúmenes.

Para KPIs globales de línea:

```text
A = tiempo_productivo_total / tiempo_planificado_total
P = (unidades_buenas × ciclo_ideal) / tiempo_productivo_total
Q = unidades_buenas / unidades_procesadas
```

Y entre réplicas:

```text
media ± t(0.975, n-1) × s / √n
```

Nunca promedio simple de ratios por estación sin ponderar por tiempo o volumen.

---

# 26. 🔍 Pareto de pérdidas

Proceso:

```text
categorías de pérdida (fallas, cambios, blocking, starvation, calidad)
      ↓
minutos por categoría
      ↓
ordenar descendente
      ↓
porcentaje acumulado
```

El gráfico mostrará barras, línea acumulada y prioridades de investigación.

---

# 27. 🚨 Centro de excepciones

Ejemplo:

```text
PRIORIDAD 1
S02-SELL-01
Utilización: 96%
Blocking upstream: 34%
Cpk: 0.96
Contribución a pérdida de throughput: 41%
```

El ranking deberá explicar **por qué** algo aparece como prioridad (score compuesto documentado).

---

# 28. 🧠 Motor de diagnóstico/investigación

El diagnóstico será de **apoyo a la investigación**, no de causalidad automática.

Ejemplo:

```text
S02 con alta utilización
+
B1 frecuentemente lleno
+
S01 con blocking alto
```

Resultado:

> "La evidencia sugiere que S02 restringe el flujo; S01 pierde tiempo bloqueada. Investigue balanceo, buffer B1 y confiabilidad de S02."

Nunca se deberá afirmar automáticamente:

```text
Causa raíz = operador
```

sin evidencia.

---

# 29. 💰 Análisis de impacto/pérdidas

Cadena:

```text
Minutos de pérdida
   ↓
Unidades no producidas
   ↓
Impacto económico estimado
```

Parámetros:

```text
costo_por_unidad
margen_por_unidad
costo_hora_parada
pérdida_estimada
```

El resultado se presentará como **estimación**.

---

# 30. 💡 Análisis What-If

Ejemplo de escenarios:

```text
S0: línea base
S1: buffer B1 de 10 → 30
S2: MTTR de S02 de 8 → 5 min
S3: segunda selladora en paralelo
S4: velocidad de S01 +5%
```

Comparación:

```text
ΔOEE con IC
Δthroughput con IC
Δpérdidas estimadas
```

Regla:

> Un escenario solo se declara superior si la diferencia es mayor que la incertidumbre (IC no superpuestos). Nunca se mostrará como mejora garantizada.

---

# 31. 🕒 Actualización de reportes

Cada reporte mostrará:

```text
Generado: AAAA-MM-DD HH:MM
Config: config/line_config.yaml (hash o versión)
Réplicas: N · Seed base: 42
```

No se deberá inventar metadata. Todo derivado de la ejecución real.

---

# 32. 🛡️ Puerta de Calidad de Configuración (Config Gate)

Flujo:

```text
YAML DE CONFIGURACIÓN
    ↓
VALIDACIÓN
    ↓
PASE ───────────► SIMULACIÓN
    │
    └────────────► FALLO
                       ↓
                 DETENER SIMULACIÓN
```

Validaciones:

- esquema y tipos;
- rate_upm > 0;
- 0 ≤ cycle_time_std ≤ 1;
- mtbf_min > 0 y mttr_min > 0;
- 0 < quality_rate ≤ 1;
- buffer_capacity ≥ 0;
- warmup < duración;
- replications ≥ 1;
- ids únicos y flujo conectado (upstream/downstream coherentes).

---

# 33. 🧠 Por qué el Config Gate es obligatorio

Una simulación con parámetros inválidos puede ser peor que no tener simulación.

Ejemplo:

```text
mtbf = 0  → división por cero / fallas infinitas
rate = 0  → throughput cero sin explicación
warmup = duración → KPIs vacíos
```

En software industrial, la validación protege:

- decisiones;
- confianza;
- trazabilidad;
- interpretación.

---

# 34. 🖥️ Plataforma: de CLI a Dash

Estado actual: CLI + reportes (HTML/PNG/Excel).

La interfaz evolucionará a:

```text
Dash
Dash Bootstrap Components
Plotly
HTML/CSS
```

Razón de negocio:

> construir un gemelo digital interactivo donde el usuario explore escenarios sin tocar YAML.

Dash permitirá arquitectura de componentes, callbacks y estado, coherente con el estándar del portafolio.

---

# 35. 🎨 Lenguaje visual

La interfaz será:

- oscura;
- minimalista;
- industrial;
- compacta;
- de alta densidad informativa;
- con estados semánticos.

Paleta conceptual:

```text
NORMAL  → verde / turquesa
VIGILAR → amarillo
PRIORIDAD → rojo
```

Regla:

> **Los colores representan estado operativo, sin decoración.**

---

# 36. 🖥️ Principio del panel de control

Diseño conceptual:

```text
┌──────────────────────────────────────────────────────────┐
│ PRODUCTION DIGITAL TWIN ● SISTEMA LISTO                  │
│ Simulación de eventos discretos y análisis de capacidad  │
├──────────────────────────────────────────────────────────┤
│ CENTRO DE CONTROL                                        │
│ Escenario | Réplicas | Seed | Producto | Configuración   │
├──────────────────────────────────────────────────────────┤
│ SALUD DE LÍNEA                                           │
│ OEE | A | P | Q | Throughput | WIP                       │
├──────────────────────────────────────────────────────────┤
│ MONTE CARLO                                              │
│ IC 95% OEE | violines | histogramas | semiancho          │
├──────────────────────────────────────────────────────────┤
│ CUELLOS DE BOTELLA            │ CAPACIDAD                │
│ heatmap utilización/blocking  │ Cp / Cpk / LSL / USL     │
├──────────────────────────────────────────────────────────┤
│ PARETO DE PÉRDIDAS              │ WHAT-IF / IMPACTO      │
├──────────────────────────────────────────────────────────┤
│ Config Gate: APROBADA | Generado: AAAA-MM-DD HH:MM       │
└──────────────────────────────────────────────────────────┘
```

---

# 37. 🎛️ Centro de control

Filtros principales:

```text
Escenario
Configuración
Réplicas
Seed
Estación
Variable
```

Los filtros serán dependientes.

Ejemplo:

```text
Estación = S02-SELL-01
    ↓
Opciones de variable
    ↓
solo ciclo, utilización, blocking de S02
```

---

# 38. 🔄 Callbacks Dash

Patrón general:

```text
ENTRADA
  ↓
CALLBACK
  ↓
SIMULACIÓN / CACHÉ
  ↓
FIGURAS
```

Ejemplos:

```text
Cambio de escenario → recalcular o leer caché → actualizar KPIs
Cambio de estación → actualizar heatmap y capacidad
```

---

# 39. 🗃️ Estado

Se utilizará:

```text
dcc.Store + caché de resultados por escenario
```

Separando:

```text
ESTADO DE UI
≠
RESULTADOS CRUDOS POR RÉPLICA
≠
ANÁLISIS AGREGADO
```

La finalidad es evitar resimular innecesariamente.

---

# 40. 📁 Arquitectura objetivo

```text
production-digital-twin/
│
├── main.py                        # CLI actual
├── app.py                         # Dash (evolución)
│
├── config/
│   ├── line_config.yaml
│   ├── scenarios.yaml
│   └── theme_config.yaml
│
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── config_loader.py
│   ├── validation.py
│   ├── simulator.py
│   ├── oee.py
│   ├── bottleneck.py
│   ├── capability.py
│   ├── statistics.py
│   ├── scenarios.py
│   ├── impact.py
│   └── reporter.py
│
├── dashboard/
│   ├── layout.py
│   ├── components/
│   │   ├── header.py
│   │   ├── filters.py
│   │   ├── kpi_cards.py
│   │   ├── charts.py
│   │   └── tables.py
│   └── callbacks/
│       ├── scenario.py
│       ├── kpis.py
│       ├── bottleneck.py
│       └── whatif.py
│
├── assets/
│   └── style.css
│
├── tests/
│   ├── test_config_loader.py
│   ├── test_validation.py
│   ├── test_simulator.py
│   ├── test_oee.py
│   ├── test_bottleneck.py
│   ├── test_capability.py
│   ├── test_statistics.py
│   └── test_scenarios.py
│
├── reports/
├── capturas/
├── .github/workflows/ci.yml
├── requirements.txt
├── .gitignore
├── PLAN_MAESTRO.md
├── README.md
└── LICENSE
```

---

# 41. 🧩 Responsabilidad de módulos

## `src/config_loader.py`
Carga YAML. No valida en profundidad (delega) y no simula.

## `src/validation.py`
Implementa el Config Gate. Devuelve errores explícitos.

## `src/simulator.py`
Motor SimPy. No dibuja, no escribe archivos.

## `src/oee.py`
Cálculo ISO 22400 y agregaciones. No dibuja.

## `src/bottleneck.py`
Score compuesto y ranking. No dibuja.

## `src/capability.py`
Cp/Cpk y clasificación. No dibuja.

## `src/statistics.py`
IC 95%, semiancho, comparación de escenarios. No dibuja.

## `src/scenarios.py`
Define y parametriza escenarios What-If.

## `src/impact.py`
Pérdidas económicas estimadas.

## `src/reporter.py`
HTML/PNG/Excel. No calcula lógica de negocio.

## `dashboard/components/` y `dashboard/callbacks/`
Construyen y conectan la UI. No contienen fórmulas.

## `app.py`
Orquesta sin absorber lógica.

---

# 42. 🧱 Separación de intereses

Arquitectura conceptual:

```text
CONFIGURACIÓN
  ↓
VALIDACIÓN (GATE)
  ↓
SIMULACIÓN
  ↓
ANÁLISIS (OEE / CUELLOS / CAPACIDAD / IC)
  ↓
WHAT-IF / IMPACTO
  ↓
VISUALIZACIÓN
```

Evitar:

```text
main.py
  ├── valida
  ├── simula
  ├── calcula OEE
  ├── dibuja
  └── exporta
```

La separación permite probar cada capa.

---

# 43. 🧪 Estrategia de pruebas

Objetivos:

```text
Exactitud
+
Protección contra regresión
+
Confianza
```

Se cubrirán:

- config loader;
- validation (gate);
- invariantes de simulación;
- matemática de OEE;
- ranking de cuellos;
- capacidad;
- estadística (IC);
- escenarios;
- reporter (archivos generados).

---

# 44. 🧪 Casos marginales prioritarios

## Validación
- rate = 0 o negativo;
- mtbf = 0; mttr = 0;
- std fuera de [0,1];
- quality > 1;
- warmup ≥ duración;
- replications = 0;
- ids duplicados; flujo desconectado.

## Simulación
- buffer = 0 (sincronizada);
- mttr > mtbf (línea colapsada);
- una estación infinitamente rápida (no debe romper);
- replications = 1 → IC indefinido (warning explícito).

## Capacidad
- n < 2;
- USL <= LSL;
- sigma = 0;
- media cerca de un límite.

## Estadística
- varianza cero;
- n pequeño;
- comparación de escenarios con IC superpuestos.

---

# 45. ✅ Puertas de calidad

Antes de cada lanzamiento:

```text
pytest
↓
python -m compileall -q src tests
↓
flake8 (o equivalente)
↓
prueba de humo: python main.py --replications 5
↓
verificación de reportes generados
↓
git diff / git status
```

La aplicación no se considera lista porque "abre".

---

# 46. 💻 Terminal, Bash y entorno IA

Comandos fundamentales:

```bash
cd production-digital-twin
ls -la
find . -maxdepth 3 -type f | sort
source venv/bin/activate
python --version
which python
pytest -q
python main.py --replications 10 --no-dashboard
```

Cada comando será enseñado con:

```text
¿Qué hace?
¿Por qué lo usamos?
¿Qué resultado esperamos?
¿Qué puede salir mal?
```

## Entorno Qwen Coder (ya configurado)

```text
MPLBACKEND=Agg          → gráficos sin pantalla (nube)
PYTHONUNBUFFERED=1      → logs inmediatos
PYTHONPATH=.            → imports de src/
script: pip install -r requirements.txt + pytest + smoke run
```

La IA asiste, pero **toda decisión técnica se defiende con este plan maestro**.

---

# 47. 🐍 Entorno virtual

Crear:

```bash
python -m venv venv
```

Activar:

```bash
source venv/bin/activate
```

Instalar:

```bash
pip install -r requirements.txt
```

---

# 48. 🚀 Ejecución

Punto de entrada actual:

```bash
python main.py --replications 50 --config config/line_config.yaml
```

Futuro:

```bash
python app.py
```

La documentación reflejará el comando real, no uno hipotético.

---

# 49. 🔀 Flujo de trabajo de Git

Antes de modificar:

```bash
git status
git diff
```

Después:

```bash
git add .
git commit -m "feat: ..."
git push origin main
```

Convención: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`.

Nunca commit mecánico sin revisar cambios.

---

# 50. 🧹 `.gitignore`

Mínimo:

```text
venv/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
.env
reports/*.html
reports/*.xlsx
```

Nunca subir secretos, cachés ni entorno virtual.

---

# 51. 🔄 CI/CD

GitHub Actions deberá ejecutar:

```text
push / pull request
       ↓
instalar dependencias
       ↓
pytest
       ↓
compileall / lint
       ↓
smoke run (5 réplicas)
       ↓
APROBADO / REPROBADO
```

---

# 52. 📦 Dependencias

Base actual:

```text
simpy
numpy
scipy
pandas
plotly
matplotlib
openpyxl
pyyaml
rich
pytest
pytest-cov
```

Futuras, solo si se justifican:

```text
dash
dash-bootstrap-components
```

`requirements.txt` deberá reflejar el entorno real.

---

# 53. 🧭 Trayectoria del usuario

La interfaz deberá responder en este orden:

```text
1. ¿Qué línea estoy simulando?
2. ¿Qué OEE espero con su incertidumbre?
3. ¿Dónde está el cuello de botella?
4. ¿Cuánta variabilidad tolera el proceso?
5. ¿El proceso es capaz (Cp/Cpk)?
6. ¿Qué pasa si invierto / cambio parámetros?
7. ¿Cuál es el impacto potencial?
```

---

# 54. 🏭 Uso empresarial del producto

## Paso 1 — Calibración
Hoy: parámetros de ingeniería (YAML). Mañana: ajustar distribuciones con historial real (MES/SCADA/CSV).

## Paso 2 — Config Gate
Sin configuración válida no hay simulación.

## Paso 3 — Línea base
OEE, cuellos, capacidad con IC.

## Paso 4 — What-If
Escenarios de inversión y mantenimiento.

## Paso 5 — Decisión
El gemelo prioriza y cuantifica, pero no sustituye Gemba, 5 Why, Ishikawa ni mantenimiento.

---

# 55. 🗄️ Evolución del backend

Primera versión:

```text
YAML (parámetros de ingeniería)
```

Segunda:

```text
CSV de historial → ajuste de distribuciones (scipy.stats)
```

Futura:

```text
SQL / integración MES
```

La capa de simulación y análisis se mantendrá desacoplada de la fuente.

> poder cambiar la fuente de datos sin reescribir la lógica de OEE, cuellos y capacidad.

---

# 56. 🚧 Hoja de ruta

## Fase 0 — Línea base
auditoría; Git; pruebas; documentación; PLAN_MAESTRO.

## Fase 1 — Modelo industrial
estaciones; buffers; IDs; productos; escenarios.

## Fase 2 — Config Gate
validación robusta de YAML; errores explícitos.

## Fase 3 — Motor de simulación
SimPy; blocking/starvation; fallas; invariantes.

## Fase 4 — Análisis
OEE ISO 22400; cuellos de botella; Pareto de pérdidas.

## Fase 5 — Capacidad
Cp/Cpk; clasificación; casos límite.

## Fase 6 — Estadística de salida
IC 95%; semiancho; comparación de escenarios.

## Fase 7 — What-If / Impacto
escenarios; pérdidas económicas estimadas.

## Fase 8 — Reportes
HTML/PNG/Excel ejecutivos; metadata real.

## Fase 9 — UI Dash
tema industrial; centro de control; caché de escenarios.

## Fase 10 — Calidad de software
cobertura; lint; CI; limpieza.

## Fase 11 — Portafolio
README; capturas; GIF del dashboard; release.

---

# 57. 🥇 Prioridades

```text
Exactitud
    ↓
realismo industrial
    ↓
validez estadística
    ↓
UX
    ↓
pulido visual
```

No al revés.

---

# 58. 🚨 Reglas de oro

1. No presentar simulación como planta real.
2. No afirmar causalidad desde correlación simple.
3. No interpretar OEE sin declarar supuestos (warmup, réplicas, seed).
4. No confundir límites de especificación con intervalos de confianza.
5. No calcular KPIs con denominadores inválidos (tiempo = 0).
6. No mezclar lógica de simulación con visualización.
7. No aceptar configuración inválida silenciosamente.
8. No agregar funcionalidades sin propósito.
9. Toda funcionalidad analítica importante debe tener pruebas.
10. Toda decisión de arquitectura importante queda documentada.

---

# 59. 🧑‍🏫 Método de aprendizaje

Cada intervención técnica seguirá:

```text
1. Explica el problema.
2. Explica la idea de ingeniería.
3. Explica el concepto de Python / SimPy.
4. Escribe el código.
5. Ejecuta el código.
6. Inspecciona la salida.
7. Verifica contra invariantes.
8. Analiza casos límite.
9. Haz commit.
10. Documenta el aprendizaje.
```

Nunca reducir el proceso a "copia y pega".

---

# 60. 🧪 Definición de Hecho

Una funcionalidad queda terminada cuando:

```text
Funciona
+
Validada
+
Probada
+
Documentada
+
Integrada
```

Si solamente aparece en pantalla, todavía no está terminada.

---

# 61. 🎤 Entrevista técnica

Al final deberás poder explicar:

> "Desarrollé un gemelo digital de una línea de envasado mediante simulación de eventos discretos con SimPy. Diseñé un modelo de estaciones y buffers finitos con fallas MTBF/MTTR y variabilidad de ciclo, construí una puerta de validación de configuración antes de simular, e implementé OEE según ISO 22400, detección de cuellos de botella por score compuesto, capacidad Cp/Cpk y análisis Monte Carlo con intervalos de confianza. Sobre esa base añadí un motor What-If para evaluar escenarios de inversión y mantenimiento con comparación estadística, y reportes ejecutivos HTML/PNG/Excel. La lógica analítica quedó separada de la visualización y cubierta por pruebas automatizadas."

La meta es que esta explicación sea verdadera porque el proyecto realmente lo implementará.

---

# 62. 📝 Registro de cambios

Cada modificación relevante:

```text
## AAAA-MM-DD — Cambio

### ¿Qué cambió?
...
### ¿Por qué?
...
### Archivos
...
### Pruebas
...
### Resultado
...
### Aprendizaje
...
```

---

# 63. 📌 Estado inicial de esta especificación

```text
Dominio 🟡 Definido
Modelo de línea (estaciones + buffers) ✅ Definido
Motor SimPy ✅ Línea base existente
OEE ISO 22400 ✅ Línea base existente
Cuellos de botella ✅ Línea base existente
Monte Carlo + seeds ✅ Línea base existente
Dashboard HTML / PNG / Excel ✅ Línea base existente
Config Gate 🟡 Parcial (robustizar)
Estadística de salida (IC) 🟡 Parcial
Pareto de pérdidas ⏳ Planificado
What-If / escenarios ⏳ Planificado
Impacto económico ⏳ Planificado
UI Dash ⏳ Planificado
Cobertura de tests ⏳ Planificado
CI/CD 🟡 Parcial
README final ✅ Definido
PLAN_MAESTRO ✅ Este documento
```

El código histórico tenía estructura distinta. Esa diferencia no se ocultará: el nuevo modelo será implementado y validado.

---

# 64. 🚀 Primer bloque real de trabajo

Orden obligatorio:

```text
AUDITORÍA
  ↓
MODELO
  ↓
CONFIG GATE
  ↓
SIMULACIÓN
  ↓
ANÁLISIS
  ↓
ESTADÍSTICA
  ↓
WHAT-IF
  ↓
DASH
  ↓
PRUEBAS
  ↓
CI
  ↓
PORTAFOLIO
```

Primera intervención técnica:

1. auditar el repositorio actual;
2. revisar `config_loader.py` y `validation`;
3. confirmar pruebas existentes;
4. conservar lógica analítica útil;
5. cerrar el modelo industrial (IDs, buffers, escenarios);
6. endurecer el Config Gate;
7. añadir estadística de salida (IC);
8. implementar escenarios What-If;
9. actualizar pruebas;
10. iniciar migración a Dash.

No se empieza por CSS.

---

# 65. 🏁 Objetivo final

```text
                 PRODUCTION DIGITAL TWIN
                          │
                          ▼
                  CONFIGURACIÓN YAML
                          │
                          ▼
                   CONFIG GATE
                          │
                          ▼
                SIMULACIÓN (SimPy)
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
           OEE        CUELLOS      CAPACIDAD
             │            │            │
             └────────────┼────────────┘
                          ▼
                 ESTADÍSTICA (IC 95%)
                          │
                          ▼
                  WHAT-IF / IMPACTO
                          │
                          ▼
               SOPORTE A LA DECISIÓN
                          │
                          ▼
                  MEJORA CONTINUA
```

La aplicación debe demostrar:

> **Sé modelar una línea de producción, validar sus supuestos, simularla con eventos discretos, analizar su desempeño con estadística válida, detectar restricciones de flujo y convertir esos resultados en soporte para decisiones de capacidad e inversión.**

La tecnología es el medio:

```text
Python · SimPy · NumPy · SciPy · Pandas · Plotly · Pytest · Git · GitHub Actions · Dash
```

La propuesta profesional es:

```text
Simulación de procesos
+
Ingeniería de producción
+
Estadística industrial
+
Inteligencia Operativa
```

---

# 66. 🧠 Principio final

El proyecto no busca fingir que es una planta real.

Busca demostrar que sabemos:

```text
modelar un problema industrial
        +
construir supuestos plausibles
        +
validarlos
        +
simularlos correctamente
        +
analizarlos con estadística válida
        +
visualizarlos profesionalmente
        +
convertirlos en soporte para decisiones
```

La definición de realismo será:

```text
Realista ≠ Complejidad falsa

Realista =
relaciones correctas (conservación, blocking, starvation)
+
lógica de proceso plausible
+
estadísticas válidas
+
supuestos rastreables
+
interfaz utilizable
+
software reproducible
```

Este será el estándar 10/10 para toda la construcción.
