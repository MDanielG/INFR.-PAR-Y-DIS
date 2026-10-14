# Juego de la Vida de Conway: secuencial vs. paralelo (Python)

Simulación del Juego de la Vida con dos versiones:

- **Secuencial:** un solo proceso, sirve como línea base.
- **Paralela:** varios procesos (`multiprocessing`) que se reparten el tablero por bloques de filas, con memoria compartida, doble buffer y barreras de sincronización.

Incluye un benchmark que compara ambas versiones y genera gráficas de rendimiento.

## Estructura del proyecto

```
juego_vida_py/
├── common.py       # Reglas del juego y utilidades compartidas
├── secuencial.py   # Versión secuencial (un proceso)
├── paralelo.py     # Versión paralela (varios procesos)
├── benchmark.py    # Mide el rendimiento y genera gráficas
└── README.md
```

## Requisitos

- Python 3.8 o superior.
- `matplotlib`, solo si quieres generar las gráficas del benchmark.

Verifica tu versión de Python:

```bash
python --version
```

En Windows puedes usar `py` en lugar de `python`. En Linux/macOS usa `python3` si `python` no apunta a la versión 3.

## Instalación

Abre una terminal dentro de la carpeta del proyecto:

```bash
cd juego_vida_py
```

Instala matplotlib con el mismo intérprete que ejecutará el código:

```bash
python -m pip install matplotlib
```

En Windows con el lanzador `py`:

```bash
py -m pip install matplotlib
```

Usar `python -m pip` (y no solo `pip`) garantiza que el paquete se instale en la misma instalación de Python que ejecuta los scripts.

## Cómo ejecutar

### 1. Versión secuencial

```bash
python secuencial.py <filas> <columnas> <generaciones>
```

Ejemplos:

```bash
python secuencial.py 15 30 10      # tablero pequeño: muestra la generación inicial y la final
python secuencial.py 400 400 20    # tablero grande: solo muestra el resumen
```

Si no pasas argumentos, usa 300x300 y 20 generaciones.

### 2. Versión paralela

```bash
python paralelo.py <filas> <columnas> <generaciones> <procesos>
```

Ejemplos:

```bash
python paralelo.py 15 30 10 4      # tablero pequeño con 4 procesos
python paralelo.py 400 400 20 8    # tablero grande con 8 procesos
```

Si no pasas argumentos, usa 300x300, 20 generaciones y 4 procesos.

### 3. Benchmark (comparación y gráficas)

```bash
python benchmark.py <generaciones> <repeticiones>
```

Ejemplos:

```bash
python benchmark.py            # valores por defecto: 20 generaciones, 2 repeticiones
python benchmark.py 20 2       # equivalente al anterior
python benchmark.py 10 1       # prueba rápida
python benchmark.py 50 3       # más estable, tarda más
```

## Significado de los parámetros

| Parámetro | Dónde se usa | Significado |
|---|---|---|
| `filas`, `columnas` | secuencial, paralelo | Tamaño del tablero |
| `generaciones` | los tres | Cuántos pasos de tiempo se simulan |
| `procesos` | paralelo | Número de procesos que se reparten el tablero |
| `repeticiones` | benchmark | Cuántas veces se repite cada medición. Se conserva el menor tiempo para reducir el ruido |

Los tamaños de tablero (`tamanos`) y los números de procesos que usa el benchmark se definen dentro de la función `main()` de `benchmark.py`:

```python
tamanos = [100, 200, 400, 800]
hilos = [h for h in (1, 2, 4, 8) if h <= nucleos]
```

Edita esas líneas para probar otros valores.

## Cómo interpretar la salida

Ejemplo:

```
SECUENCIAL | tablero: 400x400 | gens: 20 | tiempo: 1.4053 s | vivas: 7153 | checksum: 581244705
PARALELO   | tablero: 400x400 | gens: 20 | procesos: 8 | tiempo: 0.4962 s | vivas: 7153 | checksum: 581244705
```

| Campo | Significado |
|---|---|
| `tiempo` | Segundos que tardó el cálculo de las generaciones |
| `vivas` | Células vivas en el tablero final |
| `checksum` | Huella numérica del tablero final (cuántas vivas y en qué posiciones) |

**Verificación de corrección:** `vivas` y `checksum` deben ser idénticos en secuencial y paralelo cuando parten del mismo tablero inicial. Si difieren, hay un error en la paralelización.

**Métricas de rendimiento** (el benchmark las imprime):

- **Speedup** = tiempo secuencial / tiempo paralelo.
- **Eficiencia** = speedup / número de procesos.

Con el ejemplo anterior: speedup ≈ 2,83x y eficiencia ≈ 35%.

## Resultados del benchmark

Al terminar, el benchmark imprime en consola una línea por cada combinación de tamaño y procesos, e incluye la verificación (`OK` si los checksums coinciden). Además genera tres gráficas PNG en la misma carpeta:

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
| `No se pudo importar matplotlib` o aviso de que no está instalado | `pip` y `python` apuntan a instalaciones distintas | Instala con `python -m pip install matplotlib` |
| `python` no se reconoce (Windows) | Python no está en el PATH | Usa `py` o reinstala marcando "Add Python to PATH" |
| `python` abre otra versión (Linux/macOS) | `python` apunta a Python 2 | Usa `python3` |
| Error `externally-managed-environment` (Linux) | El sistema protege su Python | Crea un entorno virtual: `python3 -m venv venv`, luego `source venv/bin/activate` e instala ahí |
| El benchmark tarda demasiado | Python puro es lento con tableros grandes | Reduce `tamanos` en `benchmark.py` o usa menos generaciones |
| El paralelo es más lento que el secuencial | Tablero pequeño: el costo de crear procesos y sincronizar supera el trabajo útil | Es normal; prueba con tableros más grandes |
| El speedup no mejora al subir de procesos | Más procesos que núcleos físicos disponibles | Limita los procesos al número de núcleos de tu equipo |

## Notas

- El tablero inicial se genera con una semilla fija en `common.py`, por eso todas las ejecuciones parten del mismo estado y los resultados son comparables.
- En Windows y macOS, `multiprocessing` exige que el código de arranque esté bajo `if __name__ == "__main__":`. Los scripts ya lo respetan.
- Para ver la teoría detrás del proyecto (Ley de Amdahl, Taxonomía de Flynn, descomposición por dominio), consulta los PDFs de la materia.