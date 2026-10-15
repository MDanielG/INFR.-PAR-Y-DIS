import random


def inicializar(filas, cols, seed=100):
    """Tablero aleatorio como lista plana. Misma semilla significa mismo tablero,
    así secuencial y paralelo parten del mismo estado."""
    rnd = random.Random(seed)
    return [1 if rnd.random() < 0.3 else 0 for _ in range(filas * cols)]


def calcular_filas(act, sig, filas, cols, ini, fin):
    """Calcula la siguiente generación SOLO para las filas [ini, fin).
    Lee de 'act' y escribe en 'sig' (doble buffer). Los bordes se consideran muertos."""
    cero = [0] * (cols + 2)
    for f in range(ini, fin):
        # Filas vecinas con una columna de ceros a cada lado (evita comprobar bordes)
        arriba = [0] + list(act[(f - 1) * cols:f * cols]) + [0] if f > 0 else cero
        medio = [0] + list(act[f * cols:(f + 1) * cols]) + [0]
        abajo = [0] + list(act[(f + 1) * cols:(f + 2) * cols]) + [0] if f < filas - 1 else cero

        nueva = [0] * cols
        for c in range(cols):
            vecinos = (arriba[c] + arriba[c + 1] + arriba[c + 2]
                       + medio[c] + medio[c + 2]
                       + abajo[c] + abajo[c + 1] + abajo[c + 2])
            if medio[c + 1]:                       # célula viva
                nueva[c] = 1 if (vecinos == 2 or vecinos == 3) else 0
            else:                                  # célula muerta
                nueva[c] = 1 if vecinos == 3 else 0
        sig[f * cols:(f + 1) * cols] = nueva


def contar_vivas(g):
    return sum(g)


def checksum(g):
    """Permite verificar que secuencial y paralelo dan EXACTAMENTE el mismo resultado."""
    return sum(i + 1 for i, v in enumerate(g) if v) % (2 ** 64)


def mostrar(g, filas, cols, titulo):
    print(titulo)
    for f in range(filas):
        print("".join("🟥" if g[f * cols + c] else "⬛" for c in range(cols)))
    print()