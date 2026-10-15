# Juego de la Vida de Conway: secuencial vs. paralelo (Python)

Simulación del Juego de la Vida con dos versiones:

- **Secuencial:** un solo proceso, sirve como línea base.
- **Paralela:** varios procesos (`multiprocessing`) que se reparten el tablero por bloques de filas, con memoria compartida, doble buffer y barreras de sincronización.

Incluye una **interfaz gráfica** para ver el juego animado y comparar las dos versiones, y un **benchmark** que mide el rendimiento y genera gráficas.

## Inicio rápido

```bash
python -m pip install matplotlib
python interfaz.py
```

En la ventana: elige el tamaño, las generaciones y los procesos, pulsa **Simular secuencial** y luego **Simular paralelo**. Abajo a la izquierda aparecen el speedup y la verificación del resultado.

## Estructura del proyecto

```
INFR.-PAR-Y-DIS-Parcial_1/
├── common.py       # Reglas del juego y utilidades compartidas
├── secuencial.py   # Versión secuencial (un proceso)
├── paralelo.py     # Versión paralela (varios procesos)
├── benchmark.py    # Mide el rendimiento y genera las gráficas PNG
├── interfaz.py     # Interfaz gráfica: simulación animada, medición, resultados y gráficas
└── README.md
```

La interfaz no reimplementa nada: usa las reglas de `common.py`, las funciones `ejecutar()` de `secuencial.py` y `paralelo.py`, y las funciones `mejor()` y `graficar()` de `benchmark.py`.

## Requisitos

- Python 3.8 o superior.
- `tkinter` para la interfaz. Viene incluido con Python en Windows y macOS.
- `matplotlib` para las gráficas (del benchmark y de la interfaz).

Verifica tu versión de Python:

```bash
python --version
```

En Windows puedes usar `py` en lugar de `python`. En Linux/macOS usa `python3` si `python` no apunta a la versión 3.

## Instalación

Abre una terminal dentro de la carpeta del proyecto e instala matplotlib con el mismo intérprete que ejecutará el código:

```bash
python -m pip install matplotlib
```

En Windows con el lanzador `py`:

```bash
py -m pip install matplotlib
```

Usar `python -m pip` (y no solo `pip`) garantiza que el paquete se instale en la misma instalación de Python que ejecuta los scripts.

En Linux, si `tkinter` no está instalado: `sudo apt install python3-tk` (Debian/Ubuntu).

## Interfaz gráfica

```bash
python interfaz.py
```

### Ventana principal

| Elemento | Qué hace |
|---|---|
| **Tamaño del tablero** | 100, 500 o 1000 (tablero N x N). Al elegirlo se muestra la generación 0. |
| **Generaciones** | 10, 20, 50 o 100. |
| **Procesos** | 1, 2, 4 u 8 procesos para la versión paralela. Arriba se indica cuántos núcleos tiene tu equipo. |
| **Pausa entre generaciones** | Frena la animación para poder verla. **No** se suma al tiempo medido. |
| **▶ Simular secuencial** | Anima el juego calculado por un solo proceso (células en verde). |
| **▶ Simular paralelo** | Anima el juego calculado por procesos reales. Cada bloque de filas se pinta con el color de su proceso, y la leyenda indica qué filas calcula cada uno (P1, P2, …). |
| **■ Detener** | Corta la simulación en curso. Ese tiempo no se guarda. |
| **⏱ Medir tiempos** | Mide la secuencial y la paralela **sin animación**, llamando directamente a `secuencial.ejecutar()` y `paralelo.ejecutar()`. |
| **📊 Resultados y gráficas** | Abre la ventana de resultados (ver abajo). |
| **Recuadros SECUENCIAL / PARALELO** | Tiempo de cálculo en vivo; al terminar muestran también las vivas y el checksum. |
| **Speedup / Verificación** | Aparecen cuando las dos versiones se corrieron con el mismo tamaño y generaciones. «✔ mismo resultado» significa que los checksums coinciden. |

**¿Qué tiempo se mide durante la animación?** Solo el cálculo de cada generación. El dibujo y la pausa quedan por fuera del cronómetro, igual que en `secuencial.py` y `paralelo.py`. En la versión paralela, el arranque de los procesos tampoco se mide.

**Cómo funciona la animación paralela:** los procesos se reparten las filas igual que en `paralelo.py`, con el mismo `RawArray` y doble buffer. La diferencia es que avanzan **una generación a la vez**: la interfaz les da la señal con una barrera, ellos calculan sus filas, se sincronizan en otra barrera y la interfaz dibuja el resultado antes de pedir la siguiente.

En tableros de 1000x1000 la vista dibuja 1 de cada 2 celdas para que quepa en pantalla; el cálculo sí usa el tablero completo.

### Ventana «Resultados y gráficas»

- **Pestaña Mediciones:** tabla con todas las ejecuciones: versión, tablero, generaciones, procesos, tiempo, speedup, eficiencia, vivas, checksum, verificación (`OK` / `¡DISTINTO!`) y origen (`Animación`, `Medición` o `Benchmark`). El speedup de cada fila paralela se calcula contra la secuencial del mismo tamaño, generaciones y origen.
- **Pestañas Tiempo vs tamaño / Tiempo vs procesos / Speedup:** muestran las tres imágenes PNG que genera `benchmark.graficar()`. Son exactamente las mismas gráficas del benchmark por consola. Si ya ejecutaste `python benchmark.py`, aparecen al abrir la ventana.
- **🚀 Benchmark completo:** mide 100, 500 y 1000 con 1, 2, 4 y 8 procesos, usando las generaciones elegidas y las **repeticiones** indicadas (con `benchmark.mejor()` se conserva el menor tiempo). Llena la tabla y regenera las gráficas. Con 1000x1000 puede tardar varios minutos.
- **📈 Graficar mis mediciones:** genera las gráficas solo con lo que ya mediste en la sesión (para las generaciones elegidas). Necesita, para cada tamaño, la secuencial y la paralela con los mismos procesos.
- **🗑 Limpiar tabla:** borra las mediciones de la sesión.

Las gráficas se guardan como PNG en la carpeta del proyecto, listas para el informe.

## Uso por consola

### 1. Versión secuencial

```bash
python secuencial.py <filas> <columnas> <generaciones>
```

```bash
python secuencial.py 15 30 10      # tablero pequeño: muestra la generación inicial y la final
python secuencial.py 400 400 20    # tablero grande: solo muestra el resumen
```

Si no pasas argumentos, usa 300x300 y 20 generaciones.

### 2. Versión paralela

```bash
python paralelo.py <filas> <columnas> <generaciones> <procesos>
```

```bash
python paralelo.py 15 30 10 4      # tablero pequeño con 4 procesos
python paralelo.py 400 400 20 8    # tablero grande con 8 procesos
```

Si no pasas argumentos, usa 300x300, 20 generaciones y 4 procesos.

### 3. Benchmark

```bash
python benchmark.py <generaciones> <repeticiones>
```

```bash
python benchmark.py            # valores por defecto: 20 generaciones, 2 repeticiones
python benchmark.py 10 1       # prueba rápida
python benchmark.py 50 3       # más estable, tarda más
```

Los tamaños y procesos del benchmark por consola se definen en `main()` de `benchmark.py`:

```python
tamanos = [100, 200, 400, 800]
hilos = [h for h in (1, 2, 4, 8) if h <= nucleos]
```

Edita esas líneas para probar otros valores. (El benchmark de la interfaz usa 100, 500 y 1000 con 1, 2, 4 y 8 procesos.)

## Significado de los parámetros

| Parámetro | Dónde se usa | Significado |
|---|---|---|
| `filas`, `columnas` | secuencial, paralelo, interfaz | Tamaño del tablero |
| `generaciones` | todos | Cuántos pasos de tiempo se simulan |
| `procesos` | paralelo, interfaz | Número de procesos que se reparten el tablero |
| `repeticiones` | benchmark, interfaz | Cuántas veces se repite cada medición. Se conserva el menor tiempo para reducir el ruido |

## Cómo interpretar los resultados

Ejemplo de salida por consola:

```
SECUENCIAL | tablero: 400x400 | gens: 20 | tiempo: 1.4053 s | vivas: 7153 | checksum: 581244705
PARALELO   | tablero: 400x400 | gens: 20 | procesos: 8 | tiempo: 0.4962 s | vivas: 7153 | checksum: 581244705
```

| Campo | Significado |
|---|---|
| `tiempo` | Segundos que tardó el cálculo de las generaciones |
| `vivas` | Células vivas en el tablero final |
| `checksum` | Huella numérica del tablero final (cuántas vivas y en qué posiciones) |

**Verificación de corrección:** `vivas` y `checksum` deben ser idénticos en secuencial y paralelo cuando parten del mismo tablero inicial. Si difieren, hay un error en la paralelización. La interfaz lo comprueba sola (`OK` / `✔ mismo resultado`).

**Métricas de rendimiento:**

- **Speedup** = tiempo secuencial / tiempo paralelo.
- **Eficiencia** = speedup / número de procesos.

Con el ejemplo anterior: speedup ≈ 2,83x y eficiencia ≈ 35%.

**Gráficas generadas:**

- `grafica_tiempo_vs_tamano.png`: tiempo de ejecución según el tamaño del tablero.
- `grafica_tiempo_vs_procesos.png`: tiempo de ejecución según el número de procesos.
- `grafica_speedup.png`: speedup según el número de procesos, comparado con el ideal.

## Cómo funciona (resumen)

- **Reglas de Conway:** una célula viva sobrevive con 2 o 3 vecinos vivos y muere en los demás casos; una célula muerta nace con exactamente 3 vecinos vivos.
- **Tablero:** lista plana de `filas * columnas` valores (1 = viva, 0 = muerta). Los bordes se consideran muertos.
- **División del trabajo:** cada proceso calcula un bloque de filas contiguas.
- **Doble buffer:** en cada generación se lee de un buffer y se escribe en otro, así que los procesos no se pisan y no se necesitan locks.
- **Sincronización:** una barrera al final de cada generación impide que un proceso avance antes de que todos terminen la actual.
- **Memoria compartida:** el tablero vive en `RawArray`, visible para todos los procesos.
- **Procesos y no hilos:** el GIL de Python impide que los hilos ejecuten código Python en paralelo real. `multiprocessing` evita esa limitación.

## Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| `matplotlib no está instalado` | `pip` y `python` apuntan a instalaciones distintas | Instala con `python -m pip install matplotlib` |
| `No module named 'tkinter'` (Linux) | Tu distribución trae tkinter aparte | `sudo apt install python3-tk` |
| `python` no se reconoce (Windows) | Python no está en el PATH | Usa `py` o reinstala marcando "Add Python to PATH" |
| `python` abre otra versión (Linux/macOS) | `python` apunta a Python 2 | Usa `python3` |
| Error `externally-managed-environment` (Linux) | El sistema protege su Python | Crea un entorno virtual: `python3 -m venv venv`, luego `source venv/bin/activate` e instala ahí |
| La animación de 1000x1000 va lenta | Python puro tarda en calcular cada generación de 1 millón de celdas | Es normal; usa 100 o 500 para ver la animación fluida, o más procesos |
| El benchmark tarda demasiado | Python puro es lento con tableros grandes | Usa menos generaciones o 1 repetición |
| El paralelo es más lento que el secuencial | Tablero pequeño: el costo de crear procesos y sincronizar supera el trabajo útil | Es normal; prueba con tableros más grandes |
| El paralelo con 1 proceso es más lento que el secuencial | La memoria compartida (`RawArray`) y las barreras tienen costo extra | Es esperado; el speedup aparece con 2 o más procesos en tableros grandes |
| El speedup no mejora al subir de procesos | Más procesos que núcleos físicos disponibles | Limita los procesos al número de núcleos de tu equipo |

## Notas

- El tablero inicial se genera con una semilla fija en `common.py`, por eso todas las ejecuciones parten del mismo estado y los resultados son comparables.
- En Windows y macOS, `multiprocessing` exige que el código de arranque esté bajo `if __name__ == "__main__":`. Todos los scripts, incluida la interfaz, ya lo respetan.
- En Windows, la barra de título de la interfaz toma el color oscuro del fondo (color exacto en Windows 11, modo oscuro en Windows 10).
- Para ver la teoría detrás del proyecto (Ley de Amdahl, Taxonomía de Flynn, descomposición por dominio), consulta los PDFs de la materia.
