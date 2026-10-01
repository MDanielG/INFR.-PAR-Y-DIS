import threading
import time
import random
from functools import reduce
from collections import defaultdict


# Generar 100.000 ventas
productos = [
    ("laptop", "tecnologia"),
    ("mouse", "tecnologia"),
    ("tablet", "tecnologia"),
    ("teclado", "tecnologia"),
    ("camisa", "ropa"),
    ("pantalon", "ropa"),
    ("zapatos", "ropa"),
    ("chaqueta", "ropa"),
    ("cafe", "alimentos"),
    ("chocolate", "alimentos"),
    ("arroz", "alimentos"),
    ("leche", "alimentos")
]

ventas = []

#GENERADOR DE REGISTROS DE VENDAS
for i in range(100000):
    producto, categoria = random.choice(productos)
    monto = random.randint(5000, 3000000)

    ventas.append((producto, categoria, monto))


def map_function(ventas_seccion, resultados, posicion):
    resultado_parcial = []

    for venta in ventas_seccion:
        producto, categoria, monto = venta
        resultado_parcial.append((categoria, monto))

    resultados[posicion] = resultado_parcial


def reduce_function(agrupado):
    resultado = {}

    for categoria, montos in agrupado.items():
        resultado[categoria] = reduce(lambda a, b: a + b, montos)

    return resultado


if __name__ == "__main__":

    # Inicio del tiempo del MapReduce
    inicio = time.perf_counter()

    numero_hilos = 4

    tamaño_seccion = len(ventas) // numero_hilos

    secciones = []

    for i in range(numero_hilos):
        inicio_seccion = i * tamaño_seccion

        if i == numero_hilos - 1:
            fin_seccion = len(ventas)
        else:
            fin_seccion = inicio_seccion + tamaño_seccion

        secciones.append(ventas[inicio_seccion:fin_seccion])
#---------------------------------------
    #FASE MAP
#---------------------------------------
    resultados = [None] * numero_hilos
    hilos = []

    for i in range(numero_hilos):

        hilo = threading.Thread(
            target=map_function,
            args=(secciones[i], resultados, i)
        )

        hilos.append(hilo)
        hilo.start()

    for hilo in hilos:
        hilo.join()

    pares = []

    for resultado in resultados:
        pares.extend(resultado)

    print("\nSalida del MAP:")
    print(f"Se procesaron {len(pares):,} ventas")


#---------------------------------------
    #FASE SHUFFLE
#---------------------------------------
    agrupado = defaultdict(list)

    for categoria, monto in pares:
        agrupado[categoria].append(monto)

    print("\nSalida del SHUFFLE:")

    for categoria, montos in agrupado.items():
        print(f"{categoria}: {len(montos):,} ventas")


#---------------------------------------
#FASE REDUCE
#---------------------------------------

    resultado = reduce_function(agrupado)


    # Fin del tiempo del MapReduce
    fin = time.perf_counter()

    tiempo_total = fin - inicio


    #RESULTADOS

    print("\nResultado final (total de ventas por categoría):")

    for categoria, total in sorted(resultado.items()):
        print(f"{categoria}: ${total:,.2f}")

    print(f"\nTiempo total de ejecución MapReduce: {tiempo_total:.6f} segundos")