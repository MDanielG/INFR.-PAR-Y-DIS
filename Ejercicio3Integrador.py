"""
Ejercicio Integrador

  - SMP : cada bloque se asigna a un hilo (ThreadPoolExecutor).
  - SIMD: dentro de cada hilo, NumPy suma las filas del bloque con
          instrucciones vectorizadas (axis=1) y luego combina esas sumas.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

N = 10_000       
B = 1_000        
REPETICIONES = 5  
SEMILLA = 42
DTYPE = np.int64  
NUCLEOS = os.cpu_count() or 1


def crear_matriz(n):
    rng = np.random.default_rng(SEMILLA)
    return rng.integers(0, 101, size=(n, n), dtype=DTYPE)


def generar_bloques(n, b):
    return [(i, j) for i in range(0, n, b) for j in range(0, n, b)]


def medir(funcion, *args):
    tiempos = []
    resultado = None
    for _ in range(REPETICIONES):
        t0 = time.perf_counter()
        resultado = funcion(*args)
        tiempos.append(time.perf_counter() - t0)
    return resultado, sum(tiempos) / len(tiempos)


def suma_bloque_simd(arr, fi, ci, b):
    bloque = arr[fi:fi + b, ci:ci + b]
    sumas_filas = bloque.sum(axis=1)
    return int(sumas_filas.sum())


#1 Versión secuencial
def suma_secuencial(arr, n, b):
    return sum(suma_bloque_simd(arr, fi, ci, b) for fi, ci in generar_bloques(n, b))


#2 Híbrida SMP + SIMD
def suma_hibrida(arr, n, b, hilos):
    bloques = generar_bloques(n, b)  
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        futuros = [pool.submit(suma_bloque_simd, arr, fi, ci, b) for fi, ci in bloques]
        parciales = [f.result() for f in futuros]   
    return sum(parciales)                      


#main
if __name__ == "__main__":
    n_bloques = (N // B) ** 2
    print(f"Matriz {N}x{N}, bloques {B}x{B} -> {n_bloques} bloques")
    print(f"Núcleos lógicos detectados: {NUCLEOS}")
    print(f"Promedio de {REPETICIONES} repeticiones\n")

    t0 = time.perf_counter()
    arr = crear_matriz(N)
    print(f"Matriz creada en {time.perf_counter() - t0:.2f} s "
          f"({arr.nbytes / 1e6:.0f} MB)\n")

    # Referencia: suma directa de NumPy sobre toda la matriz
    referencia = int(arr.sum())

    # Versión secuencial (línea base)
    r_seq, t_seq = medir(suma_secuencial, arr, N, B)
    assert r_seq == referencia, "La suma secuencial no coincide con la referencia"

    # Híbrida con distinta cantidad de hilos
    configuraciones = sorted({1, 2, 4, NUCLEOS, n_bloques})
    resultados = []
    for h in configuraciones:
        r, t = medir(suma_hibrida, arr, N, B, h)
        assert r == referencia, f"La suma con {h} hilos no coincide"
        resultados.append((h, r, t))

    print(f"{'Versión':<28}{'Hilos':>7}{'Suma':>16}{'Tiempo (s)':>13}{'Speedup':>10}")
    print("-" * 74)
    print(f"{'Secuencial (NumPy)':<28}{1:>7}{r_seq:>16}{t_seq:>13.6f}{1.0:>9.2f}x")
    for h, r, t in resultados:
        print(f"{'Híbrida SMP + SIMD':<28}{h:>7}{r:>16}{t:>13.6f}{t_seq / t:>9.2f}x")

    print("\nVerificación: todas las sumas coinciden con arr.sum() ->", referencia)