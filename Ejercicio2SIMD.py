"""
Ejercicio 2: Arquitectura SIMD (Single Instruction, Multiple Data)
Multiplicación de matrices 1000x1000: NumPy vs bucle tradicional en Python.
"""

import sys
import time

import numpy as np

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
SEMILLA = 42


def multiplicar_numpy(a, b):
    """NumPy: delega en BLAS (código C/Fortran con instrucciones SIMD)."""
    return a @ b  


def multiplicar_bucle(a, b):
    """Bucle tradicional en Python: triple bucle, O(n^3) operaciones."""
    n = len(a)
    c = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            suma = 0.0
            for k in range(n):
                suma += a[i][k] * b[k][j]
            c[i][j] = suma
    return c


def cronometrar(funcion, *args):
    t0 = time.perf_counter()
    resultado = funcion(*args)
    return resultado, time.perf_counter() - t0


if __name__ == "__main__":
    print(f"Matrices {N}x{N} con números aleatorios (semilla {SEMILLA})")
    rng = np.random.default_rng(SEMILLA)
    a_np = rng.random((N, N))
    b_np = rng.random((N, N))
    a_list, b_list = a_np.tolist(), b_np.tolist()  # mismos datos para ambas versiones

    #NumPy(se promedian 5 repeticiones: es muy rápido y el ruido pesa)
    tiempos_np = []
    for _ in range(5):
        c_np, t = cronometrar(multiplicar_numpy, a_np, b_np)
        tiempos_np.append(t)
    t_np = sum(tiempos_np) / len(tiempos_np)

    #Bucle Python (una sola ejecución: es muy lento)
    print("Ejecutando bucle en Python puro (puede tardar)...")
    c_list, t_py = cronometrar(multiplicar_bucle, a_list, b_list)

    #Verificación de correctitud
    correcto = np.allclose(np.array(c_list), c_np)
    print(f"\nResultados equivalentes: {correcto}\n")

    print(f"{'Implementación':<28}{'Tiempo (s)':>14}{'Speedup':>12}")
    print("-" * 54)
    print(f"{'Bucle Python':<28}{t_py:>14.4f}{1.0:>11.1f}x")
    print(f"{'NumPy (a @ b)':<28}{t_np:>14.6f}{t_py / t_np:>11.1f}x")
