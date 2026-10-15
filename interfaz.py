"""Interfaz gráfica del Juego de la Vida de Conway (secuencial vs. paralelo).

Ejecutar:  python interfaz.py

- Simula el juego con animación, en versión secuencial o paralela (procesos reales).
- Mide el tiempo de cálculo mientras anima (el dibujo NO se cuenta).
- Mide tiempos sin animación con las funciones ejecutar() de secuencial.py y paralelo.py.
- Muestra una tabla de resultados y las gráficas que genera benchmark.py
  (benchmark.graficar), y permite lanzar el benchmark completo desde la ventana.

Solo usa tkinter (viene con Python). Las gráficas necesitan matplotlib.
"""
import base64
import os
import queue
import threading
import time
from multiprocessing import Barrier, Process, RawArray, freeze_support
from threading import BrokenBarrierError

from common import calcular_filas, checksum, contar_vivas, inicializar

CARPETA = os.path.dirname(os.path.abspath(__file__))
GRAFICAS = [
    ("Tiempo vs tamaño", "grafica_tiempo_vs_tamano.png"),
    ("Tiempo vs procesos", "grafica_tiempo_vs_procesos.png"),
    ("Speedup", "grafica_speedup.png"),
]

TAMANOS = (100, 500, 1000)
GENERACIONES = (10, 20, 50, 100)
PROCESOS = (1, 2, 4, 8)
LADO_LIENZO = 600                     # píxeles del área de dibujo

# Colores
FONDO = "#14161c"
PANEL = "#1d2029"
BORDE = "#2c3040"
TEXTO = "#e6e6e6"
TENUE = "#9aa0b0"
ACENTO = "#4f8cff"
MUERTA = "#0f1115"
COLOR_SEC = "#5be37d"
COLORES_PROC = ["#ff5c5c", "#4dd0e1", "#ffd54f", "#ba68c8",
                "#ff8a65", "#64b5f6", "#f06292", "#aed581"]


# --------------------------------------------------------------------------
# Trabajador de la animación paralela (debe estar a nivel de módulo para que
# multiprocessing lo encuentre también en Windows/macOS).
# --------------------------------------------------------------------------
def trabajador_animado(ini, fin, buf0, buf1, filas, cols, gens, inicio, ir, listo):
    """Igual que paralelo.trabajador, pero avanza UNA generación cada vez que la
    interfaz lo pide (barrera 'ir') y avisa al terminarla (barrera 'listo').
    Así la interfaz puede dibujar entre generaciones sin que el dibujo cuente
    en el tiempo de cálculo."""
    bufs = (buf0, buf1)
    try:
        inicio.wait()
        for g in range(gens):
            ir.wait()
            calcular_filas(bufs[g % 2], bufs[(g + 1) % 2], filas, cols, ini, fin)
            listo.wait()
    except BrokenBarrierError:            # la interfaz pidió detener
        pass


def bloques_de_filas(filas, nh):
    """Mismo reparto que paralelo.py: bloques contiguos, el resto a los primeros."""
    base, resto = divmod(filas, nh)
    res = []
    for i in range(nh):
        ini = i * base + min(i, resto)
        res.append((ini, ini + base + (1 if i < resto else 0)))
    return res


# --------------------------------------------------------------------------
# Conversión rápida tablero -> imagen PPM (sin librerías externas)
# --------------------------------------------------------------------------
def _rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def _mezcla(c1, c2, t):
    a, b = _rgb(c1), _rgb(c2)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


class Pintor:
    """Convierte el tablero (bytes 0/1) en una imagen PPM. Cada bloque de filas
    puede tener su propio color (en la versión paralela, el color del proceso).
    Para tableros más grandes que el lienzo se toma 1 de cada 'paso' celdas."""

    def __init__(self, n, bloques, colores_vivas, colores_muertas):
        self.n = n
        self.paso = max(1, -(-n // LADO_LIENZO))           # ceil(n / LADO)
        self.m = len(range(0, n, self.paso))                # lado reducido
        self.zoom = max(1, LADO_LIENZO // self.m)
        self.cabecera = b"P6 %d %d 255\n" % (self.m, self.m)
        self.bloques = []
        for (ini, fin), viva, muerta in zip(bloques, colores_vivas, colores_muertas):
            r_ini, r_fin = -(-ini // self.paso), -(-fin // self.paso)
            if r_fin <= r_ini:
                continue
            tablas = []
            for canal in range(3):
                t = bytearray(256)
                t[0], t[1] = _rgb(muerta)[canal], _rgb(viva)[canal]
                tablas.append(bytes(t))
            self.bloques.append((r_ini, r_fin, tablas))

    def imagen(self, datos):
        n, k, m = self.n, self.paso, self.m
        if k > 1:
            datos = b"".join(datos[f * n:(f + 1) * n:k] for f in range(0, n, k))
        salida = bytearray(m * m * 3)
        for r_ini, r_fin, (tr, tg, tb) in self.bloques:
            trozo = datos[r_ini * m:r_fin * m]
            a, b = r_ini * m * 3, r_fin * m * 3
            salida[a:b:3] = trozo.translate(tr)
            salida[a + 1:b:3] = trozo.translate(tg)
            salida[a + 2:b:3] = trozo.translate(tb)
        return self.cabecera + bytes(salida)


def barra_oscura(ventana, color=FONDO):
    """Pinta la barra de título de la ventana con el color del fondo (solo Windows).
    Windows 11: color exacto (DWMWA_CAPTION_COLOR). Windows 10: modo oscuro.
    En otros sistemas no hace nada."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ventana.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(ventana.winfo_id()) or ventana.winfo_id()
        dwm = ctypes.windll.dwmapi
        oscuro = ctypes.c_int(1)
        for atributo in (20, 19):                 # DWMWA_USE_IMMERSIVE_DARK_MODE (nuevo / viejo)
            if dwm.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(oscuro), ctypes.sizeof(oscuro)) == 0:
                break
        r, g, b = _rgb(color)
        colorref = ctypes.c_int(r | (g << 8) | (b << 16))       # formato 0x00BBGGRR
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref), ctypes.sizeof(colorref))  # fondo
        texto = ctypes.c_int(0xE6E6E6)
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(texto), ctypes.sizeof(texto))        # texto
        # Forzar el redibujado de la barra
        ventana.withdraw()
        ventana.deiconify()
    except Exception:
        pass


def ppm_a_png(ppm):
    """Plan B por si la versión de Tk no lee PPM en memoria: lo convierte a PNG (base64)."""
    import struct
    import zlib
    cab, rgb = ppm.split(b"\n", 1)
    _, w, h, _ = cab.split()
    w, h = int(w), int(h)
    filas = b"".join(b"\x00" + rgb[f * w * 3:(f + 1) * w * 3] for f in range(h))

    def trozo(tipo, datos):
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))
    png = (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + trozo(b"IDAT", zlib.compress(filas, 1)) + trozo(b"IEND", b""))
    return base64.b64encode(png)


# --------------------------------------------------------------------------
# Hilos de cálculo (no tocan tkinter: se comunican por una cola)
# --------------------------------------------------------------------------
class Simulacion(threading.Thread):
    """Corre la simulación animada en segundo plano y envía cuadros a la interfaz."""

    def __init__(self, app, modo, n, gens, nh):
        super().__init__(daemon=True)
        self.app, self.modo, self.n, self.gens = app, modo, n, gens
        self.nh = max(1, min(nh, n)) if modo == "par" else 1
        self.detener = threading.Event()
        self.dibujado = threading.Event()
        self.procesos = []
        self.barreras = []

    # Espera a que la interfaz dibuje el cuadro (más el retardo elegido)
    def _esperar_dibujo(self):
        while not self.dibujado.wait(0.2):
            if self.detener.is_set():
                return
        self.dibujado.clear()
        retardo = self.app.retardo_ms / 1000
        if retardo:
            self.detener.wait(retardo)

    def _cuadro(self, pintor, g, datos, total):
        self.app.cola.put(("cuadro", self.modo, g, self.gens, pintor.imagen(datos),
                           pintor.zoom, datos.count(1), total))
        self._esperar_dibujo()

    def run(self):
        try:
            if self.modo == "seq":
                self._secuencial()
            else:
                self._paralelo()
        except Exception as e:                      # se muestra en la interfaz
            self.app.cola.put(("error", f"{type(e).__name__}: {e}"))
        finally:
            self._limpiar()

    def _secuencial(self):
        n, gens = self.n, self.gens
        pintor = Pintor(n, [(0, n)], [COLOR_SEC], [MUERTA])
        act = inicializar(n, n)
        sig = [0] * (n * n)
        total = 0.0
        self._cuadro(pintor, 0, bytes(act), total)
        for g in range(gens):
            if self.detener.is_set():
                return self.app.cola.put(("detenido", self.modo))
            t0 = time.perf_counter()
            calcular_filas(act, sig, n, n, 0, n)
            act, sig = sig, act
            total += time.perf_counter() - t0
            self._cuadro(pintor, g + 1, bytes(act), total)
        self.app.cola.put(("fin", {"modo": "Secuencial", "n": n, "gens": gens, "procesos": 1,
                                   "tiempo": total, "vivas": contar_vivas(act),
                                   "checksum": checksum(act), "origen": "Animación"}))

    def _paralelo(self):
        n, gens, nh = self.n, self.gens, self.nh
        bloques = bloques_de_filas(n, nh)
        colores = [COLORES_PROC[i % len(COLORES_PROC)] for i in range(nh)]
        pintor = Pintor(n, bloques, colores, [_mezcla(MUERTA, c, 0.13) for c in colores])
        self.app.cola.put(("leyenda", bloques, colores))

        buf0 = RawArray('B', inicializar(n, n))
        buf1 = RawArray('B', n * n)
        bufs = (buf0, buf1)
        inicio, ir, listo = Barrier(nh + 1), Barrier(nh + 1), Barrier(nh + 1)
        self.barreras = [inicio, ir, listo]
        for ini, fin in bloques:
            p = Process(target=trabajador_animado,
                        args=(ini, fin, buf0, buf1, n, n, gens, inicio, ir, listo), daemon=True)
            self.procesos.append(p)
            p.start()

        self.app.cola.put(("estado", f"Arrancando {nh} proceso(s)…"))
        inicio.wait(timeout=120)               # todos listos: el arranque no se mide
        total = 0.0
        self._cuadro(pintor, 0, bytes(buf0), total)
        for g in range(gens):
            if self.detener.is_set():
                return self.app.cola.put(("detenido", self.modo))
            t0 = time.perf_counter()
            ir.wait()                           # ¡calculen la generación g!
            listo.wait()                        # todos terminaron (barrera)
            total += time.perf_counter() - t0
            self._cuadro(pintor, g + 1, bytes(bufs[(g + 1) % 2]), total)
        for p in self.procesos:
            p.join()
        final = bufs[gens % 2]
        self.app.cola.put(("fin", {"modo": "Paralelo", "n": n, "gens": gens, "procesos": nh,
                                   "tiempo": total, "vivas": contar_vivas(final),
                                   "checksum": checksum(final), "origen": "Animación"}))

    def _limpiar(self):
        for b in self.barreras:
            b.abort()
        for p in self.procesos:
            p.join(timeout=1)
            if p.is_alive():
                p.terminate()

    def parar(self):
        self.detener.set()
        self.dibujado.set()
        for b in self.barreras:
            b.abort()


def tarea_medir(app, n, gens, nh):
    """'Medir tiempos': usa directamente secuencial.ejecutar() y paralelo.ejecutar()."""
    from secuencial import ejecutar as ejecutar_seq
    from paralelo import ejecutar as ejecutar_par
    try:
        app.cola.put(("estado", f"Midiendo secuencial {n}x{n}…"))
        r = ejecutar_seq(n, n, gens)
        app.cola.put(("resultado", dict(r, modo="Secuencial", n=n, gens=gens, procesos=1,
                                        origen="Medición")))
        app.cola.put(("estado", f"Midiendo paralelo {n}x{n} con {nh} proceso(s)…"))
        r = ejecutar_par(n, n, gens, nh)
        app.cola.put(("resultado", dict(r, modo="Paralelo", n=n, gens=gens,
                                        procesos=max(1, min(nh, n)), origen="Medición")))
        app.cola.put(("listo", "Medición terminada."))
    except Exception as e:
        app.cola.put(("error", f"{type(e).__name__}: {e}"))


def tarea_graficar(app, seq, par, tamanos, hilos):
    """Genera las 3 gráficas con benchmark.graficar() (las mismas PNG del benchmark)."""
    try:
        import matplotlib
        matplotlib.use("Agg")                     # dibujar sin ventana, desde un hilo
        import benchmark
        cwd = os.getcwd()
        os.chdir(CARPETA)                         # graficar() guarda en la carpeta actual
        try:
            benchmark.graficar(seq, par, tamanos, hilos)
        finally:
            os.chdir(cwd)
        app.cola.put(("graficas", None))
    except ImportError:
        app.cola.put(("error", "matplotlib no está instalado.\n"
                               "Instálalo con:  python -m pip install matplotlib"))
    except Exception as e:
        app.cola.put(("error", f"{type(e).__name__}: {e}"))


def tarea_benchmark(app, gens, rep):
    """Benchmark completo: 100, 500 y 1000 con 1, 2, 4 y 8 procesos (como benchmark.main)."""
    import benchmark
    from secuencial import ejecutar as ejecutar_seq
    from paralelo import ejecutar as ejecutar_par
    tamanos, hilos = list(TAMANOS), list(PROCESOS)
    seq, par = {}, {h: {} for h in hilos}
    pasos, hecho = len(tamanos) * (1 + len(hilos)), 0
    try:
        for n in tamanos:
            app.cola.put(("progreso", hecho, pasos, f"Secuencial {n}x{n}…"))
            rs = benchmark.mejor(ejecutar_seq, rep, n, n, gens)
            seq[n] = rs["tiempo"]
            app.cola.put(("resultado", dict(rs, modo="Secuencial", n=n, gens=gens,
                                            procesos=1, origen="Benchmark")))
            hecho += 1
            for h in hilos:
                app.cola.put(("progreso", hecho, pasos, f"Paralelo {n}x{n} con {h} proceso(s)…"))
                rp = benchmark.mejor(ejecutar_par, rep, n, n, gens, h)
                par[h][n] = rp["tiempo"]
                app.cola.put(("resultado", dict(rp, modo="Paralelo", n=n, gens=gens,
                                                procesos=h, origen="Benchmark")))
                hecho += 1
        app.cola.put(("progreso", pasos, pasos, "Generando gráficas…"))
        tarea_graficar(app, seq, par, tamanos, hilos)
        app.cola.put(("listo", "Benchmark completo terminado."))
    except Exception as e:
        app.cola.put(("error", f"{type(e).__name__}: {e}"))


# --------------------------------------------------------------------------
# Interfaz
# --------------------------------------------------------------------------
class App:
    def __init__(self, raiz):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.raiz = raiz
        self.cola = queue.Queue()
        self.sim = None
        self.ocupado = False
        self.resultados = []
        self.ultimo = {"Secuencial": None, "Paralelo": None}
        self.retardo_ms = 30
        self.ventana_res = None
        self.imagen = None

        self.n = tk.IntVar(value=100)
        self.gens = tk.IntVar(value=50)
        self.procs = tk.IntVar(value=min(4, os.cpu_count() or 1))

        raiz.title("Juego de la Vida de Conway")
        raiz.configure(bg=FONDO)
        raiz.protocol("WM_DELETE_WINDOW", self.cerrar)
        self._estilos()
        self._construir()
        self._dibujar_inicial()
        barra_oscura(raiz)
        self.raiz.after(30, self._revisar_cola)

    # ---------- construcción ----------
    def _estilos(self):
        s = self.ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXTO,
                    rowheight=24, bordercolor=BORDE)
        s.configure("Treeview.Heading", background=BORDE, foreground=TEXTO, relief="flat")
        s.map("Treeview", background=[("selected", ACENTO)])
        s.configure("TNotebook", background=FONDO, borderwidth=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=TENUE, padding=(14, 6))
        s.map("TNotebook.Tab", background=[("selected", BORDE)], foreground=[("selected", TEXTO)])
        s.configure("Horizontal.TProgressbar", background=ACENTO, troughcolor=PANEL)

    def _boton(self, padre, texto, cmd, color=BORDE, ancho=None):
        b = self.tk.Button(padre, text=texto, command=cmd, bg=color, fg=TEXTO,
                           activebackground=ACENTO, activeforeground="white", relief="flat",
                           bd=0, padx=10, pady=7, cursor="hand2", font=("Segoe UI", 10, "bold"),
                           disabledforeground="#5c6172")
        if ancho:
            b.configure(width=ancho)
        return b

    def _grupo_opciones(self, padre, titulo, valores, var, fmt=str):
        tk = self.tk
        tk.Label(padre, text=titulo, bg=PANEL, fg=TENUE, font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 3))
        fila = tk.Frame(padre, bg=PANEL)
        fila.pack(fill="x")
        botones = []

        def elegir(v):
            var.set(v)
            for b, bv in botones:
                b.configure(bg=ACENTO if bv == v else BORDE)
            self._dibujar_inicial()

        for v in valores:
            b = self._boton(fila, fmt(v), lambda v=v: elegir(v))
            b.pack(side="left", expand=True, fill="x", padx=2)
            botones.append((b, v))
        elegir(var.get())
        return [b for b, _ in botones]

    def _tarjeta(self, padre, titulo, color):
        tk = self.tk
        f = tk.Frame(padre, bg=FONDO, highlightbackground=color, highlightthickness=2)
        f.pack(fill="x", pady=5)
        tk.Label(f, text=titulo, bg=FONDO, fg=color, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        tiempo = tk.Label(f, text="— s", bg=FONDO, fg=TEXTO, font=("Consolas", 20, "bold"))
        tiempo.pack(anchor="w", padx=10)
        info = tk.Label(f, text="Sin ejecutar", bg=FONDO, fg=TENUE, font=("Segoe UI", 9), justify="left")
        info.pack(anchor="w", padx=10, pady=(0, 6))
        return tiempo, info

    def _construir(self):
        tk = self.tk
        izq = tk.Frame(self.raiz, bg=PANEL, padx=14, pady=10)
        izq.pack(side="left", fill="y")
        der = tk.Frame(self.raiz, bg=FONDO, padx=14, pady=12)
        der.pack(side="left", fill="both", expand=True)

        tk.Label(izq, text="Juego de la Vida", bg=PANEL, fg=TEXTO,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(izq, text=f"Tu equipo tiene {os.cpu_count() or '?'} núcleo(s)", bg=PANEL,
                 fg=TENUE, font=("Segoe UI", 9)).pack(anchor="w")

        self.controles = []
        self.controles += self._grupo_opciones(izq, "Tamaño del tablero (N x N)", TAMANOS, self.n)
        self.controles += self._grupo_opciones(izq, "Generaciones", GENERACIONES, self.gens)
        self.controles += self._grupo_opciones(izq, "Procesos (versión paralela)", PROCESOS, self.procs)

        tk.Label(izq, text="Pausa entre generaciones (ms) — solo visual", bg=PANEL, fg=TENUE,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 0))
        escala = tk.Scale(izq, from_=0, to=500, orient="horizontal", bg=PANEL, fg=TEXTO,
                          troughcolor=BORDE, highlightthickness=0, bd=0,
                          command=lambda v: setattr(self, "retardo_ms", int(v)))
        escala.set(self.retardo_ms)
        escala.pack(fill="x")

        acciones = tk.Frame(izq, bg=PANEL)
        acciones.pack(fill="x", pady=(10, 0))
        self.b_seq = self._boton(acciones, "▶  Simular secuencial", lambda: self.simular("seq"), "#2f6b43")
        self.b_par = self._boton(acciones, "▶  Simular paralelo", lambda: self.simular("par"), "#7a2f3a")
        self.b_stop = self._boton(acciones, "■  Detener", self.detener)
        self.b_medir = self._boton(acciones, "⏱  Medir tiempos (sin animación)", self.medir)
        self.b_res = self._boton(acciones, "📊  Resultados y gráficas", self.abrir_resultados, "#28407a")
        for b in (self.b_seq, self.b_par, self.b_stop, self.b_medir, self.b_res):
            b.pack(fill="x", pady=3)
        self.b_stop.configure(state="disabled")
        self.controles += [self.b_seq, self.b_par, self.b_medir]

        self.t_seq, self.i_seq = self._tarjeta(izq, "SECUENCIAL", COLOR_SEC)
        self.t_par, self.i_par = self._tarjeta(izq, "PARALELO", COLORES_PROC[0])
        self.l_speed = tk.Label(izq, text="Speedup: —", bg=PANEL, fg=TEXTO,
                                font=("Segoe UI", 11, "bold"), justify="left")
        self.l_speed.pack(anchor="w", pady=(4, 0))

        # Lado derecho: tablero
        self.l_titulo = tk.Label(der, text="", bg=FONDO, fg=TEXTO, font=("Segoe UI", 13, "bold"))
        self.l_titulo.pack(anchor="w")
        self.lienzo = tk.Canvas(der, width=LADO_LIENZO, height=LADO_LIENZO, bg=MUERTA,
                                highlightthickness=1, highlightbackground=BORDE)
        self.lienzo.pack(pady=8)
        self.leyenda = tk.Frame(der, bg=FONDO)
        self.leyenda.pack(anchor="w")
        self.l_estado = tk.Label(der, text="Elige la configuración y pulsa Simular.", bg=FONDO,
                                 fg=TENUE, font=("Segoe UI", 10), anchor="w", justify="left")
        self.l_estado.pack(anchor="w", fill="x", pady=(6, 0))
        tk.Label(der, text="Reglas: una célula viva sobrevive con 2 o 3 vecinas; "
                           "una muerta nace con exactamente 3.",
                 bg=FONDO, fg="#6b7183", font=("Segoe UI", 9)).pack(anchor="w")

    # ---------- dibujo ----------
    def _crear_photo(self, ppm):
        """Tk 9 acepta el PPM binario; algunas versiones de Tk 8.6 lo quieren en base64."""
        modos = [self._modo_ppm] if getattr(self, "_modo_ppm", None) else ["bin", "b64", "png"]
        for modo in modos:
            try:
                if modo == "png":
                    img = self.tk.PhotoImage(data=ppm_a_png(ppm), format="png")
                else:
                    datos = ppm if modo == "bin" else base64.b64encode(ppm)
                    img = self.tk.PhotoImage(data=datos, format="ppm")
                self._modo_ppm = modo
                return img
            except self.tk.TclError:
                continue
        raise RuntimeError("Tk no pudo leer la imagen del tablero")

    def _poner_imagen(self, ppm, zoom):
        img = self._crear_photo(ppm)
        if zoom > 1:
            img = img.zoom(zoom)
        self.imagen = img
        self.lienzo.delete("all")
        w = img.width()
        off = (LADO_LIENZO - w) // 2
        self.lienzo.create_image(off + 1, off + 1, image=img, anchor="nw")

    def _dibujar_inicial(self):
        """Muestra la generación 0 de la configuración elegida (antes de simular)."""
        if not hasattr(self, "lienzo") or self.ocupado:
            return
        n = self.n.get()
        pintor = Pintor(n, [(0, n)], [TEXTO], [MUERTA])
        datos = bytes(inicializar(n, n))
        self._poner_imagen(pintor.imagen(datos), pintor.zoom)
        self._limpiar_leyenda()
        self.l_titulo.configure(text=f"Tablero {n}x{n} — generación 0")
        self.l_estado.configure(text=f"Vivas: {datos.count(1)}   ·   Elige la configuración y pulsa Simular.")

    def _limpiar_leyenda(self):
        for w in self.leyenda.winfo_children():
            w.destroy()

    def _mostrar_leyenda(self, bloques, colores):
        tk = self.tk
        self._limpiar_leyenda()
        for i, ((ini, fin), c) in enumerate(zip(bloques, colores)):
            tk.Label(self.leyenda, text="■", fg=c, bg=FONDO, font=("Segoe UI", 12)).grid(row=i // 4, column=(i % 4) * 2)
            tk.Label(self.leyenda, text=f"P{i + 1}: filas {ini}–{fin - 1}  ", fg=TENUE, bg=FONDO,
                     font=("Segoe UI", 9)).grid(row=i // 4, column=(i % 4) * 2 + 1, sticky="w")

    # ---------- acciones ----------
    def _set_ocupado(self, ocupado, animando=False):
        self.ocupado = ocupado
        for b in self.controles:
            b.configure(state="disabled" if ocupado else "normal")
        self.b_stop.configure(state="normal" if animando else "disabled")
        if self.ventana_res is not None and self.ventana_res.winfo_exists():
            for b in self.botones_res:
                b.configure(state="disabled" if ocupado else "normal")

    def simular(self, modo):
        if self.ocupado:
            return
        n, gens, nh = self.n.get(), self.gens.get(), self.procs.get()
        self._set_ocupado(True, animando=True)
        self._limpiar_leyenda()
        if modo == "seq":
            self.t_seq.configure(text="0.0000 s")
        else:
            self.t_par.configure(text="0.0000 s")
        self.sim = Simulacion(self, modo, n, gens, nh)
        self.sim.start()

    def detener(self):
        if self.sim is not None:
            self.sim.parar()
            self.l_estado.configure(text="Deteniendo…")

    def medir(self):
        if self.ocupado:
            return
        self._set_ocupado(True)
        threading.Thread(target=tarea_medir, daemon=True,
                         args=(self, self.n.get(), self.gens.get(), self.procs.get())).start()

    def cerrar(self):
        if self.sim is not None:
            self.sim.parar()
            self.sim.join(timeout=2)
        self.raiz.destroy()

    # ---------- resultados ----------
    def _agregar_resultado(self, r):
        self.resultados.append(r)
        self.ultimo[r["modo"]] = r
        self._actualizar_tarjetas()
        self._refrescar_tabla()

    def _seq_de(self, n, gens, origen=None):
        """Mejor medición secuencial para ese tamaño y generaciones
        (prefiere una del mismo origen: animación con animación, etc.)."""
        cand = [r for r in self.resultados if r["modo"] == "Secuencial" and r["n"] == n and r["gens"] == gens]
        mismo = [r for r in cand if r["origen"] == origen]
        cand = mismo or cand
        return min(cand, key=lambda r: r["tiempo"]) if cand else None

    def _actualizar_tarjetas(self):
        for modo, t, i in (("Secuencial", self.t_seq, self.i_seq), ("Paralelo", self.t_par, self.i_par)):
            r = self.ultimo[modo]
            if r is None:
                continue
            t.configure(text=f"{r['tiempo']:.4f} s")
            extra = f" · {r['procesos']} proceso(s)" if modo == "Paralelo" else ""
            i.configure(text=f"{r['n']}x{r['n']} · {r['gens']} gens{extra} · {r['origen']}\n"
                             f"Vivas: {r['vivas']} · Checksum: {r['checksum']}")
        s, p = self.ultimo["Secuencial"], self.ultimo["Paralelo"]
        if s and p and s["n"] == p["n"] and s["gens"] == p["gens"]:
            sp = s["tiempo"] / p["tiempo"] if p["tiempo"] else 0
            ok = "✔ mismo resultado" if s["checksum"] == p["checksum"] else "✘ ¡resultado distinto!"
            self.l_speed.configure(text=f"Speedup: {sp:.2f}x   Eficiencia: {sp / p['procesos'] * 100:.0f}%\n"
                                        f"Verificación: {ok}",
                                   fg="#8be39f" if s["checksum"] == p["checksum"] else "#ff7070")
        else:
            self.l_speed.configure(text="Speedup: — (simula ambas versiones\ncon el mismo tamaño y generaciones)",
                                   fg=TENUE)

    def abrir_resultados(self):
        tk, ttk = self.tk, self.ttk
        if self.ventana_res is not None and self.ventana_res.winfo_exists():
            self.ventana_res.lift()
            return
        v = tk.Toplevel(self.raiz, bg=FONDO)
        v.title("Resultados y gráficas")
        v.geometry("1000x780")
        barra_oscura(v)
        self.ventana_res = v

        barra = tk.Frame(v, bg=FONDO, padx=10, pady=8)
        barra.pack(fill="x")
        tk.Label(barra, text="Repeticiones:", bg=FONDO, fg=TENUE).pack(side="left")
        self.rep = tk.IntVar(value=1)
        tk.Spinbox(barra, from_=1, to=5, width=3, textvariable=self.rep, bg=PANEL, fg=TEXTO,
                   buttonbackground=BORDE, relief="flat").pack(side="left", padx=(4, 10))
        b1 = self._boton(barra, "🚀  Benchmark completo", self.benchmark_completo, "#28407a")
        b2 = self._boton(barra, "📈  Graficar mis mediciones", self.graficar_mediciones)
        b3 = self._boton(barra, "🗑  Limpiar tabla", self.limpiar_resultados)
        for b in (b1, b2, b3):
            b.pack(side="left", padx=3)
        self.botones_res = [b1, b2, b3]
        self.progreso = ttk.Progressbar(barra, length=180, mode="determinate")
        self.progreso.pack(side="right")
        self.l_prog = tk.Label(v, text="El benchmark completo mide 100, 500 y 1000 con 1, 2, 4 y 8 procesos "
                                       "usando las generaciones elegidas (puede tardar varios minutos).",
                               bg=FONDO, fg=TENUE, anchor="w")
        self.l_prog.pack(fill="x", padx=12)

        nb = ttk.Notebook(v)
        nb.pack(fill="both", expand=True, padx=10, pady=8)
        self.notebook = nb

        # Pestaña tabla
        ft = tk.Frame(nb, bg=FONDO)
        nb.add(ft, text="Mediciones")
        cols = ("modo", "tablero", "gens", "procs", "tiempo", "speedup", "efic", "vivas", "checksum", "verif", "origen")
        nombres = ("Versión", "Tablero", "Gens", "Procesos", "Tiempo (s)", "Speedup", "Eficiencia",
                   "Vivas", "Checksum", "Verificación", "Origen")
        anchos = (85, 80, 50, 70, 85, 70, 80, 70, 110, 95, 85)
        tabla = ttk.Treeview(ft, columns=cols, show="headings")
        for c, t, a in zip(cols, nombres, anchos):
            tabla.heading(c, text=t)
            tabla.column(c, width=a, anchor="center")
        sb = ttk.Scrollbar(ft, orient="vertical", command=tabla.yview)
        tabla.configure(yscrollcommand=sb.set)
        tabla.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        tabla.tag_configure("mal", foreground="#ff7070")
        self.tabla = tabla

        # Pestañas de gráficas (PNG generadas por benchmark.graficar)
        self.lienzos_graf = []
        for titulo, archivo in GRAFICAS:
            f = tk.Frame(nb, bg="white")
            nb.add(f, text=titulo)
            lbl = tk.Label(f, bg="white", fg="#444", font=("Segoe UI", 11), justify="center")
            lbl.pack(fill="both", expand=True)
            self.lienzos_graf.append((lbl, archivo))

        self._refrescar_tabla()
        self._cargar_graficas()
        self._set_ocupado(self.ocupado, animando=self.sim is not None and self.sim.is_alive())

    def _refrescar_tabla(self):
        if self.ventana_res is None or not self.ventana_res.winfo_exists():
            return
        self.tabla.delete(*self.tabla.get_children())
        for r in self.resultados:
            s = self._seq_de(r["n"], r["gens"], r["origen"])
            if r["modo"] == "Paralelo" and s:
                sp = s["tiempo"] / r["tiempo"] if r["tiempo"] else 0
                sp_txt, ef_txt = f"{sp:.2f}x", f"{sp / r['procesos'] * 100:.0f}%"
            else:
                sp_txt = ef_txt = "—"
            if s is None or r["modo"] == "Secuencial":
                verif, tag = ("base" if r["modo"] == "Secuencial" else "sin sec."), ()
            else:
                okv = r["checksum"] == s["checksum"]
                verif, tag = ("OK" if okv else "¡DISTINTO!"), (() if okv else ("mal",))
            self.tabla.insert("", "end", tags=tag, values=(
                r["modo"], f"{r['n']}x{r['n']}", r["gens"], r["procesos"], f"{r['tiempo']:.4f}",
                sp_txt, ef_txt, r["vivas"], r["checksum"], verif, r["origen"]))

    def _cargar_graficas(self):
        if self.ventana_res is None or not self.ventana_res.winfo_exists():
            return
        self.imgs_graf = []
        for lbl, archivo in self.lienzos_graf:
            ruta = os.path.join(CARPETA, archivo)
            if os.path.exists(ruta):
                try:
                    img = self.tk.PhotoImage(file=ruta)
                    if img.width() > 1000:             # PNG de 1200 px -> 900 px
                        img = img.zoom(3).subsample(4)
                    self.imgs_graf.append(img)
                    lbl.configure(image=img, text="")
                    continue
                except Exception as e:
                    texto = f"No se pudo abrir {archivo}: {e}"
            else:
                texto = (f"Aún no existe {archivo}.\n\n"
                         "Pulsa «Benchmark completo» o «Graficar mis mediciones»,\n"
                         "o ejecuta  python benchmark.py  en la consola.")
            lbl.configure(image="", text=texto)

    def limpiar_resultados(self):
        self.resultados.clear()
        self.ultimo = {"Secuencial": None, "Paralelo": None}
        for t, i in ((self.t_seq, self.i_seq), (self.t_par, self.i_par)):
            t.configure(text="— s")
            i.configure(text="Sin ejecutar")
        self._actualizar_tarjetas()
        self._refrescar_tabla()

    def benchmark_completo(self):
        if self.ocupado:
            return
        self._set_ocupado(True)
        self.progreso.configure(value=0)
        threading.Thread(target=tarea_benchmark, daemon=True,
                         args=(self, self.gens.get(), max(1, int(self.rep.get() or 1)))).start()

    def graficar_mediciones(self):
        """Arma los datos con las mediciones de la tabla (mismas generaciones que las
        elegidas) y llama a benchmark.graficar()."""
        if self.ocupado:
            return
        from tkinter import messagebox
        gens = self.gens.get()
        seq, par = {}, {}
        for r in self.resultados:
            if r["gens"] != gens:
                continue
            if r["modo"] == "Secuencial":
                seq[r["n"]] = min(seq.get(r["n"], r["tiempo"]), r["tiempo"])
            else:
                d = par.setdefault(r["procesos"], {})
                d[r["n"]] = min(d.get(r["n"], r["tiempo"]), r["tiempo"])
        tamanos = sorted(seq)
        hilos = sorted(h for h in par if all(n in par[h] for n in tamanos))
        if not tamanos or not hilos:
            messagebox.showinfo("Faltan datos", f"Para graficar con {gens} generaciones necesitas, para cada "
                                "tamaño medido, el tiempo secuencial y el paralelo con los mismos procesos.\n\n"
                                "Simula o mide ambas versiones, o usa «Benchmark completo».",
                                parent=self.ventana_res)
            return
        self._set_ocupado(True)
        self.l_prog.configure(text=f"Graficando tamaños {tamanos} con procesos {hilos}…")
        threading.Thread(target=tarea_graficar, daemon=True,
                         args=(self, seq, par, tamanos, hilos)).start()

    # ---------- bucle de mensajes desde los hilos ----------
    def _revisar_cola(self):
        from tkinter import messagebox
        ultimo_cuadro = None
        try:
            while True:
                msg = self.cola.get_nowait()
                tipo = msg[0]
                if tipo == "cuadro":
                    ultimo_cuadro = msg
                    continue
                if ultimo_cuadro:                       # dibujar antes de procesar lo demás
                    self._dibujar_cuadro(ultimo_cuadro)
                    ultimo_cuadro = None
                if tipo == "leyenda":
                    self._mostrar_leyenda(msg[1], msg[2])
                elif tipo == "estado":
                    self.l_estado.configure(text=msg[1])
                elif tipo == "fin":
                    r = msg[1]
                    self._agregar_resultado(r)
                    self.l_estado.configure(text=f"Terminado: {r['modo'].lower()} {r['n']}x{r['n']}, "
                                                 f"{r['gens']} generaciones en {r['tiempo']:.4f} s de cálculo.")
                    self._set_ocupado(False)
                elif tipo == "detenido":
                    self.l_estado.configure(text="Simulación detenida (no se guardó el tiempo).")
                    self._set_ocupado(False)
                elif tipo == "resultado":
                    self._agregar_resultado(msg[1])
                elif tipo == "progreso":
                    _, hecho, total, texto = msg
                    if self.ventana_res is not None and self.ventana_res.winfo_exists():
                        self.progreso.configure(maximum=total, value=hecho)
                        self.l_prog.configure(text=f"[{hecho}/{total}] {texto}")
                    self.l_estado.configure(text=f"Benchmark [{hecho}/{total}] {texto}")
                elif tipo == "graficas":
                    self._cargar_graficas()
                    if self.ventana_res is not None and self.ventana_res.winfo_exists():
                        self.l_prog.configure(text=f"Gráficas guardadas en: {CARPETA}")
                        self.notebook.select(1)
                    self._set_ocupado(False)
                elif tipo == "listo":
                    self.l_estado.configure(text=msg[1])
                    self._set_ocupado(False)
                elif tipo == "error":
                    self._set_ocupado(False)
                    messagebox.showerror("Error", msg[1], parent=self.raiz)
        except queue.Empty:
            pass
        if ultimo_cuadro:
            self._dibujar_cuadro(ultimo_cuadro)
        self.raiz.after(15, self._revisar_cola)

    def _dibujar_cuadro(self, msg):
        _, modo, g, gens, datos, zoom, vivas, total = msg
        sim = self.sim
        self._poner_imagen(datos, zoom)
        nombre = "Secuencial" if modo == "seq" else f"Paralelo ({sim.nh if sim else '?'} procesos)"
        n = sim.n if sim else self.n.get()
        self.l_titulo.configure(text=f"{nombre} — tablero {n}x{n} — generación {g}/{gens}")
        self.l_estado.configure(text=f"Vivas: {vivas}   ·   Tiempo de cálculo acumulado: {total:.4f} s"
                                     + ("   ·   cada color = un proceso" if modo == "par" else ""))
        (self.t_seq if modo == "seq" else self.t_par).configure(text=f"{total:.4f} s")
        if sim is not None:
            sim.dibujado.set()


def main():
    import tkinter as tk
    raiz = tk.Tk()
    raiz.minsize(1000, 700)
    App(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    freeze_support()
    main()