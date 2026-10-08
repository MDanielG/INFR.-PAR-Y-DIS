"""
Ejercicio 1: Arquitectura SMP (Symmetric Multiprocessing)
Suma de una matriz 1000x1000 dividida en bloques de 100x100 usando hilos.
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

N = 1000          # tamaño de la matriz (N x N)
B = 100           # tamaño del bloque (B x B)
REPETICIONES = 5  # se promedia para reducir ruido en la medición
SEMILLA = 42


# ---------------------------------------------------------------- utilidades
def crear_matriz(n):
    """Matriz n x n con enteros aleatorios (lista de listas, Python puro)."""
    random.seed(SEMILLA)
    return [[random.randint(0, 100) for _ in range(n)] for _ in range(n)]


def generar_bloques(n, b):
    """Devuelve las coordenadas (fila_ini, col_ini) de cada bloque b x b."""
    return [(i, j) for i in range(0, n, b) for j in range(0, n, b)]


def medir(funcion, *args):
    """Ejecuta funcion REPETICIONES veces y retorna (resultado, tiempo_promedio)."""
    tiempos = []
    resultado = None
    for _ in range(REPETICIONES):
        t0 = time.perf_counter()
        resultado = funcion(*args)
        tiempos.append(time.perf_counter() - t0)
    return resultado, sum(tiempos) / len(tiempos)


# ------------------------------------------------- 1) Versión secuencial
def suma_secuencial(matriz):
    total = 0
    for fila in matriz:
        total += sum(fila)
    return total


# ------------------------------------- 2) Hilos, Python puro (un hilo/bloque)
def suma_bloque(matriz, fi, ci, b):
    """Tarea de cada hilo: suma de los elementos de su bloque."""
    return sum(sum(matriz[i][ci:ci + b]) for i in range(fi, fi + b))


def suma_hilos(matriz, n, b):
    bloques = generar_bloques(n, b)  # 100 bloques -> 100 tareas
    with ThreadPoolExecutor(max_workers=len(bloques)) as pool:
        futuros = [pool.submit(suma_bloque, matriz, fi, ci, b) for fi, ci in bloques]
        parciales = [f.result() for f in futuros]   # resultados parciales
    return sum(parciales)                           # combinación final


# ------------------------------------------- 3) Hilos + NumPy (libera el GIL)
def suma_bloque_np(arr, fi, ci, b):
    return int(arr[fi:fi + b, ci:ci + b].sum())


def suma_hilos_numpy(arr, n, b):
    bloques = generar_bloques(n, b)
    with ThreadPoolExecutor(max_workers=len(bloques)) as pool:
        futuros = [pool.submit(suma_bloque_np, arr, fi, ci, b) for fi, ci in bloques]
        return sum(f.result() for f in futuros)


def suma_secuencial_numpy(arr):
    return int(arr.sum())


# ---------------------------------------------------------------------- main
if __name__ == "__main__":
    print(f"Matriz {N}x{N}, bloques {B}x{B} -> {(N // B) ** 2} bloques/hilos")
    print(f"Promedio de {REPETICIONES} repeticiones\n")

    matriz = crear_matriz(N)
    arr = np.array(matriz, dtype=np.int64)

    r_seq, t_seq = medir(suma_secuencial, matriz)
    r_thr, t_thr = medir(suma_hilos, matriz, N, B)
    r_snp, t_snp = medir(suma_secuencial_numpy, arr)
    r_tnp, t_tnp = medir(suma_hilos_numpy, arr, N, B)

    # Verificación de correctitud: todas deben dar la misma suma
    assert r_seq == r_thr == r_snp == r_tnp, "Las sumas no coinciden"

    print(f"{'Versión':<34}{'Suma':>14}{'Tiempo (s)':>14}{'Speedup':>10}")
    print("-" * 72)
    filas = [
        ("Secuencial (Python puro)", r_seq, t_seq, 1.0),
        ("100 hilos (Python puro)", r_thr, t_thr, t_seq / t_thr),
        ("Secuencial (NumPy)", r_snp, t_snp, t_seq / t_snp),
        ("100 hilos (NumPy)", r_tnp, t_tnp, t_snp / t_tnp),
    ]
    for nombre, suma, t, sp in filas:
        print(f"{nombre:<34}{suma:>14}{t:>14.6f}{sp:>9.2f}x")
