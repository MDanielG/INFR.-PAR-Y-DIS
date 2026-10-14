import sys
import time
from multiprocessing import Process, RawArray, Barrier
from common import inicializar, calcular_filas, contar_vivas, checksum, mostrar


def trabajador(ini, fin, buf0, buf1, filas, cols, gens, inicio, barrera):
    """Cada proceso calcula SUS filas en cada generación.
    - Lee de bufs[g%2] y escribe en bufs[(g+1)%2]: nadie escribe donde otros leen,
      por eso NO se necesitan locks.
    - La barrera evita que un proceso empiece la generación g+1 antes de que
      todos terminen la g (las filas vecinas de otro proceso ya deben estar listas)."""
    bufs = (buf0, buf1)
    inicio.wait()                                # arranque simultáneo de todos
    for g in range(gens):
        calcular_filas(bufs[g % 2], bufs[(g + 1) % 2], filas, cols, ini, fin)
        barrera.wait()


def ejecutar(filas, cols, gens, nh, mostrar_tablero=False):
    nh = max(1, min(nh, filas))                  # no más procesos que filas
    n = filas * cols

    # Memoria compartida entre procesos (doble buffer)
    buf0 = RawArray('B', inicializar(filas, cols))
    buf1 = RawArray('B', n)

    if mostrar_tablero:
        mostrar(buf0, filas, cols, "Generacion 0:")

    inicio = Barrier(nh + 1)                     # nh procesos + el principal
    barrera = Barrier(nh)

    # División por BLOQUES DE FILAS contiguas; el resto se reparte 1 fila extra
    # a los primeros procesos para balancear la carga.
    base, resto = divmod(filas, nh)
    procesos = []
    for i in range(nh):
        ini = i * base + min(i, resto)
        fin = ini + base + (1 if i < resto else 0)
        p = Process(target=trabajador,
                    args=(ini, fin, buf0, buf1, filas, cols, gens, inicio, barrera))
        procesos.append(p)
        p.start()

    inicio.wait()                                # todos listos: empieza el cronómetro
    t0 = time.perf_counter()
    for p in procesos:
        p.join()
    t1 = time.perf_counter()

    final = list((buf0, buf1)[gens % 2])         # donde quedó la última generación

    if mostrar_tablero:
        mostrar(final, filas, cols, "Generacion final:")

    return {"tiempo": t1 - t0, "vivas": contar_vivas(final), "checksum": checksum(final)}


if __name__ == "__main__":
    filas = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    gens = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    nh = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    r = ejecutar(filas, cols, gens, nh, mostrar_tablero=(filas <= 20 and cols <= 40))
    print(f"PARALELO   | tablero: {filas}x{cols} | gens: {gens} | procesos: {nh} | "
          f"tiempo: {r['tiempo']:.4f} s | vivas: {r['vivas']} | checksum: {r['checksum']}")