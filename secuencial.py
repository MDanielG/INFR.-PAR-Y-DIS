import sys
import time
from common import inicializar, calcular_filas, contar_vivas, checksum, mostrar


def ejecutar(filas, cols, gens, mostrar_tablero=False):
    act = inicializar(filas, cols)
    sig = [0] * (filas * cols)

    if mostrar_tablero:
        mostrar(act, filas, cols, "Generacion 0:")

    t0 = time.perf_counter()
    for _ in range(gens):
        calcular_filas(act, sig, filas, cols, 0, filas)
        act, sig = sig, act                      # intercambio de buffers
    t1 = time.perf_counter()

    if mostrar_tablero:
        mostrar(act, filas, cols, "Generacion final:")

    return {"tiempo": t1 - t0, "vivas": contar_vivas(act), "checksum": checksum(act)}


if __name__ == "__main__":
    filas = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    gens = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    r = ejecutar(filas, cols, gens, mostrar_tablero=(filas <= 20 and cols <= 40))
    print(f"SECUENCIAL | tablero: {filas}x{cols} | gens: {gens} | "
          f"tiempo: {r['tiempo']:.4f} s | vivas: {r['vivas']} | checksum: {r['checksum']}")