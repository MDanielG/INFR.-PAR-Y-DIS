#Author Daniel Andres Micolta Gongora
#Codigo 202422033
    
import time
import concurrent.futures

N = 20  # Número de Fibonacci a calcular



# 1. CÁLCULO DE FIBONACCI

def fibonacci_recursivo(n):
    if n <= 1:
        return n
    return fibonacci_recursivo(n - 1) + fibonacci_recursivo(n - 2)


# ---------------------------------------------------------------------
# 2. VERSIÓN SERIAL
# ---------------------------------------------------------------------
def calcular_serial(n_elementos):
    inicio = time.perf_counter()
    resultados = [fibonacci_recursivo(i) for i in range(n_elementos)]
    tiempo = time.perf_counter() - inicio
    return resultados, tiempo


# ---------------------------------------------------------------------
# 3. VERSIÓN PARALELA
# ---------------------------------------------------------------------
def calcular_fibonacci_paralelo(n_elementos, executor_type):
    inicio = time.perf_counter()
    resultados = [None] * n_elementos

    with executor_type() as executor:
        future_a_indice = {
            executor.submit(fibonacci_recursivo, i): i
            for i in range(n_elementos)
        }

        for future in concurrent.futures.as_completed(future_a_indice):
            i = future_a_indice[future]
            resultados[i] = future.result()

    tiempo = time.perf_counter() - inicio
    return resultados, tiempo


# ---------------------------------------------------------------------
# 4. IMPRESIÓN
# ---------------------------------------------------------------------
def imprimir_resultados(nombre, resultados, tiempo):
    print(f"\n--- {nombre} ---")
    print(f"Fibonacci(0 a {len(resultados) - 1}): {resultados}")
    print(f"Tiempo de ejecución: {tiempo:.4f} segundos")


if __name__ == "__main__":
    print(f"Calculando los primeros {N} números de Fibonacci")

    #Línea base serial
    resultados_serial, tiempo_serial = calcular_serial(N)
    imprimir_resultados("SERIAL", resultados_serial, tiempo_serial)

    #Paralelo con PROCESOS
    resultados_proc, tiempo_proc = calcular_fibonacci_paralelo(
        N, concurrent.futures.ProcessPoolExecutor
    )
    imprimir_resultados("PARALELO - ProcessPoolExecutor", resultados_proc, tiempo_proc)

    #Paralelo con HILOS
    resultados_hilo, tiempo_hilo = calcular_fibonacci_paralelo(
        N, concurrent.futures.ThreadPoolExecutor
    )
    imprimir_resultados("PARALELO - ThreadPoolExecutor", resultados_hilo, tiempo_hilo)

