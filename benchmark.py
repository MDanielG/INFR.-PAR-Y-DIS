import os
import sys
from secuencial import ejecutar as ejecutar_seq
from paralelo import ejecutar as ejecutar_par


def mejor(fn, rep, *args):
    """Repite la medición 'rep' veces y devuelve la de menor tiempo (reduce el ruido)."""
    return min((fn(*args) for _ in range(rep)), key=lambda r: r["tiempo"])


def graficar(seq, par, tamanos, hilos):
    import matplotlib.pyplot as plt

    # 1) Tiempo vs tamaño del tablero
    plt.figure(figsize=(8, 5))
    plt.plot(tamanos, [seq[n] for n in tamanos], "k--o", label="Secuencial")
    for h in hilos:
        plt.plot(tamanos, [par[h][n] for n in tamanos], marker="o", label=f"{h} proceso(s)")
    plt.xlabel("Tamaño del tablero (N x N)")
    plt.ylabel("Tiempo de ejecución (s)")
    plt.title("Tiempo vs tamaño del tablero")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("grafica_tiempo_vs_tamano.png", dpi=150)
    plt.close()

    # 2) Tiempo vs número de procesos
    plt.figure(figsize=(8, 5))
    for n in tamanos:
        plt.plot(hilos, [par[h][n] for h in hilos], marker="o", label=f"{n}x{n}")
    plt.xlabel("Número de procesos")
    plt.ylabel("Tiempo de ejecución (s)")
    plt.title("Tiempo vs número de procesos")
    plt.xticks(hilos)
    plt.grid(True, alpha=0.3)
    plt.legend(title="Tablero")
    plt.tight_layout()
    plt.savefig("grafica_tiempo_vs_procesos.png", dpi=150)
    plt.close()

    # 3) Speedup vs número de procesos
    plt.figure(figsize=(8, 5))
    for n in tamanos:
        plt.plot(hilos, [seq[n] / par[h][n] for h in hilos], marker="o", label=f"{n}x{n}")
    plt.plot(hilos, hilos, "k--", label="Speedup ideal")
    plt.xlabel("Número de procesos")
    plt.ylabel("Speedup (T secuencial / T paralelo)")
    plt.title("Speedup vs número de procesos")
    plt.xticks(hilos)
    plt.grid(True, alpha=0.3)
    plt.legend(title="Tablero")
    plt.tight_layout()
    plt.savefig("grafica_speedup.png", dpi=150)
    plt.close()

    print("Gráficas generadas: grafica_tiempo_vs_tamano.png, "
          "grafica_tiempo_vs_procesos.png, grafica_speedup.png")


def main():
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rep = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    tamanos = [100, 200, 400, 800]               # ajusta según tu equipo
    nucleos = os.cpu_count() or 2
    hilos = [h for h in (1, 2, 4, 8) if h <= nucleos] or [1]

    seq, par = {}, {h: {} for h in hilos}

    for n in tamanos:
        print(f"\nTablero {n}x{n}, {gens} generaciones")
        rs = mejor(ejecutar_seq, rep, n, n, gens)
        seq[n] = rs["tiempo"]
        print(f"  Secuencial: {rs['tiempo']:.3f} s")

        for h in hilos:
            rp = mejor(ejecutar_par, rep, n, n, gens, h)
            par[h][n] = rp["tiempo"]
            ok = "OK" if rp["checksum"] == rs["checksum"] else "¡RESULTADO DISTINTO!"
            print(f"  {h} proceso(s): {rp['tiempo']:.3f} s | speedup {rs['tiempo'] / rp['tiempo']:.2f}x")


    try:
        graficar(seq, par, tamanos, hilos)
    except ImportError:
        print("matplotlib no está instalado: ejecuta 'pip install matplotlib' para generar las gráficas.")


if __name__ == "__main__":
    main()