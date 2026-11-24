import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
import calendar
import unicodedata
import tempfile
import json
import os
import hashlib
import secrets

ARCHIVO = "usuarios_escolares.json"

AZUL_OSCURO = "#0f172a"
TARJETA = "#1a224a"
AZUL = "#00c2ff"
BLANCO = "#ffffff"
SUAVE = "#a3b3d6"
FONDO = "#edf1f5"
ROJO = "#c62828"
CAMPO = "#232e5c"
BOTON_SECUNDARIO = "#203060"
BORDE = "#35416e"
AMARILLO = "#FFCC00"
AMARILLO_CLARO = "#FCFBBD"
VERDE_CLARO = "#E5F5EF"
ROJO_SUAVE = "#FCEBEC"


def cargar_usuarios():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
                if isinstance(datos, dict):
                    return datos
        except (OSError, json.JSONDecodeError):
            messagebox.showerror(
                "Error",
                "No se pudo leer el archivo de usuarios."
            )
    return {}


def guardar_usuarios():
    try:
        with open(ARCHIVO, "w", encoding="utf-8") as archivo:
            json.dump(
                usuarios_guardados,
                archivo,
                indent=4,
                ensure_ascii=False
            )
        return True
    except OSError:
        messagebox.showerror(
            "Error",
            "No se pudieron guardar los datos."
        )
        return False


def crear_hash(contrasena, sal=None):
    if sal is None:
        sal = secrets.token_hex(16)

    resultado = hashlib.pbkdf2_hmac(
        "sha256",
        contrasena.encode("utf-8"),
        bytes.fromhex(sal),
        200000
    )

    return sal, resultado.hex()


def verificar_contrasena(contrasena, datos):
    try:
        _, resultado = crear_hash(contrasena, datos["sal"])
        return secrets.compare_digest(resultado, datos["hash"])
    except (KeyError, TypeError, ValueError):
        return False


usuarios_guardados = cargar_usuarios()


def registrar_usuario():
    usuario = entrada_usuario.get().strip()
    contrasena = entrada_contrasena.get()

    if not usuario or not contrasena:
        messagebox.showwarning(
            "Datos incompletos",
            "Escribe un usuario y una contraseña."
        )
        return

    if len(usuario) < 3:
        messagebox.showwarning(
            "Usuario no válido",
            "El usuario debe tener al menos 3 caracteres."
        )
        return

    if len(contrasena) < 8:
        messagebox.showwarning(
            "Contraseña corta",
            "La contraseña debe tener al menos 8 caracteres."
        )
        return

    if usuario in usuarios_guardados:
        messagebox.showerror(
            "Cuenta existente",
            "Ese usuario ya está registrado."
        )
        return

    if var_codigo.get():
        if usuario.casefold() != "director":
            messagebox.showwarning(
                "Usuario de dirección",
                "Para la cuenta del director, escribe exactamente: Director"
            )
            return
        rol = "Director"
    else:
        rol = "Maestro"

    sal, hash_contra = crear_hash(contrasena)

    usuarios_guardados[usuario] = {
        "sal": sal,
        "hash": hash_contra,
        "rol": rol
    }

    if guardar_usuarios():
        messagebox.showinfo(
            "Cuenta creada",
            "La cuenta de "
            + rol.lower()
            + " se registró correctamente."
        )
        entrada_contrasena.delete(0, tk.END)
        entrada_codigo.delete(0, tk.END)
        var_codigo.set(False)
        mostrar_codigo()
        entrada_usuario.focus_set()


def entrar():
    usuario = entrada_usuario.get().strip()
    contrasena = entrada_contrasena.get()

    if not usuario or not contrasena:
        messagebox.showwarning(
            "Datos incompletos",
            "Escribe tu usuario y contraseña."
        )
        return

    if usuario not in usuarios_guardados:
        messagebox.showerror(
            "Cuenta no encontrada",
            "Primero debes crear tu cuenta."
        )
        return

    datos = usuarios_guardados[usuario]

    if not verificar_contrasena(contrasena, datos):
        messagebox.showerror(
            "Acceso denegado",
            "La contraseña es incorrecta."
        )
        return

    if usuario.casefold() == "director":
        rol = "Director"
        if datos.get("rol") != "Director":
            datos["rol"] = "Director"
            guardar_usuarios()
    else:
        rol = datos.get("rol", "Maestro")

    ventana.withdraw()
    abrir_panel(usuario, rol)


def desplazar_contenido_con_rueda(event, lienzo):
    """Desplaza `lienzo` con la rueda solo si el puntero está sobre su área.

    - Ignora el puntero cuando está en el menú lateral, el encabezado u
      otra ventana (por ejemplo la lista desplegable de un Combobox).
    - Si el puntero está sobre una tabla, lista o cuadro de texto que tiene
      su propio desplazamiento, esa tabla se mueve sola y la página no.
    """
    try:
        if lienzo is None or not lienzo.winfo_exists():
            return
        zona = lienzo.master
        widget = lienzo.winfo_containing(event.x_root, event.y_root)
    except (tk.TclError, KeyError):
        return

    interno = None
    while widget is not None:
        if interno is None and isinstance(
            widget, (ttk.Treeview, tk.Listbox, tk.Text)
        ):
            interno = widget
        if widget is zona:
            break
        widget = widget.master
    else:
        return

    if interno is not None:
        try:
            if tuple(interno.yview()) != (0.0, 1.0):
                return
        except tk.TclError:
            pass

    if event.num == 4:
        cantidad = -1
    elif event.num == 5:
        cantidad = 1
    elif event.delta:
        cantidad = int(-event.delta / 120)
        if cantidad == 0:
            cantidad = -1 if event.delta > 0 else 1
    else:
        return
    lienzo.yview_scroll(cantidad, "units")


MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
    "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


def normalizar_texto(texto):
    """Minúsculas y sin acentos, para buscar 'lopez' y encontrar 'López'."""
    texto = unicodedata.normalize("NFD", texto)
    return "".join(
        c for c in texto if unicodedata.category(c) != "Mn"
    ).casefold()


class SelectorFecha(tk.Frame):
    """Campo de fecha (dd/mm/aaaa) que abre un calendario al hacer clic."""

    def __init__(
        self, parent, inicial=None, fuente=("Segoe UI", 10),
        fondo="#F8FAFC", borde="#E2E8F0", acento="#356AE6",
        acento_claro="#EAF0FF", texto="#24344D", suave="#718096",
        ipady=8
    ):
        super().__init__(
            parent, bg=fondo, highlightbackground=borde,
            highlightcolor=acento, highlightthickness=1
        )
        self.fuente = fuente
        self.fondo = fondo
        self.borde = borde
        self.acento = acento
        self.acento_claro = acento_claro
        self.texto = texto
        self.suave = suave
        self.popup = None
        self.interior = None
        self.mes = 1
        self.anio = 2000

        self.var = tk.StringVar(
            value=(inicial or date.today()).strftime("%d/%m/%Y")
        )

        self.entrada = tk.Entry(
            self, textvariable=self.var, font=fuente, bg=fondo, fg=texto,
            readonlybackground=fondo, relief="flat", bd=0,
            highlightthickness=0, state="readonly", cursor="hand2"
        )
        self.entrada.pack(
            side="left", fill="x", expand=True, padx=(10, 0), ipady=ipady
        )

        self.icono = tk.Label(
            self, text="📅", bg=fondo, fg=acento, cursor="hand2",
            font=("Segoe UI Emoji", 11)
        )
        self.icono.pack(side="right", padx=(6, 10))

        self.entrada.bind("<Button-1>", self._alternar)
        self.icono.bind("<Button-1>", self._alternar)
        self.bind("<Destroy>", self._al_destruir)

    def get(self):
        return self.var.get()

    def set(self, valor):
        if isinstance(valor, date):
            valor = valor.strftime("%d/%m/%Y")
        self.var.set(valor)

    def _fecha_actual(self):
        try:
            return datetime.strptime(self.var.get(), "%d/%m/%Y").date()
        except ValueError:
            return date.today()

    def _al_destruir(self, event):
        if event.widget is self:
            self.cerrar()

    def _alternar(self, event=None):
        if self.popup is not None:
            self.cerrar()
        else:
            self.abrir()
        return "break"

    def abrir(self):
        actual = self._fecha_actual()
        self.mes, self.anio = actual.month, actual.year

        self.popup = tk.Toplevel(self)
        self.popup.overrideredirect(True)
        self.popup.configure(bg=self.borde)
        try:
            self.popup.attributes("-topmost", True)
        except tk.TclError:
            pass

        self.interior = tk.Frame(self.popup, bg="#FFFFFF", padx=10, pady=10)
        self.interior.pack(padx=1, pady=1)
        self._construir()

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        self.popup.geometry(f"+{x}+{y}")
        self.popup.focus_force()
        self.popup.bind("<FocusOut>", self._al_perder_foco)
        self.popup.bind("<Escape>", lambda e: self.cerrar())

    def _al_perder_foco(self, event=None):
        self.after(120, self._revisar_foco)

    def _revisar_foco(self):
        try:
            if self.popup is not None and self.popup.focus_displayof() is None:
                self.cerrar()
        except tk.TclError:
            self.popup = None

    def cerrar(self):
        if self.popup is not None:
            try:
                self.popup.destroy()
            except tk.TclError:
                pass
        self.popup = None
        self.interior = None

    def _cambiar_mes(self, delta):
        mes = self.mes + delta
        if mes < 1:
            mes, self.anio = 12, self.anio - 1
        elif mes > 12:
            mes, self.anio = 1, self.anio + 1
        self.mes = mes
        self._construir()

    def _elegir(self, fecha):
        self.var.set(fecha.strftime("%d/%m/%Y"))
        self.cerrar()

    def _construir(self):
        if self.interior is None:
            return
        for w in self.interior.winfo_children():
            w.destroy()

        def boton_flecha(texto, delta):
            return tk.Button(
                cabecera, text=texto, command=lambda: self._cambiar_mes(delta),
                bg="#FFFFFF", fg=self.texto, activebackground=self.acento_claro,
                activeforeground=self.acento, relief="flat", bd=0,
                cursor="hand2", font=("Segoe UI", 12, "bold"), width=3
            )

        cabecera = tk.Frame(self.interior, bg="#FFFFFF")
        cabecera.pack(fill="x", pady=(0, 8))
        boton_flecha("‹", -1).pack(side="left")
        boton_flecha("›", 1).pack(side="right")
        tk.Label(
            cabecera, text=f"{MESES[self.mes - 1]} {self.anio}",
            bg="#FFFFFF", fg=self.texto, font=("Segoe UI", 10, "bold")
        ).pack(side="left", expand=True)

        cuadro = tk.Frame(self.interior, bg="#FFFFFF")
        cuadro.pack()

        for i, d in enumerate(DIAS_SEMANA):
            tk.Label(
                cuadro, text=d, bg="#FFFFFF", fg=self.suave,
                font=("Segoe UI", 8, "bold"), width=4, pady=4
            ).grid(row=0, column=i)

        seleccionada = self._fecha_actual()
        hoy = date.today()

        for fila, semana in enumerate(
            calendar.monthcalendar(self.anio, self.mes), start=1
        ):
            for col, dia in enumerate(semana):
                if dia == 0:
                    continue
                f = date(self.anio, self.mes, dia)
                if f == seleccionada:
                    bg, fg = self.acento, "#FFFFFF"
                elif f == hoy:
                    bg, fg = self.acento_claro, self.acento
                else:
                    bg, fg = "#FFFFFF", self.texto
                tk.Button(
                    cuadro, text=str(dia), width=3,
                    command=lambda d=f: self._elegir(d),
                    bg=bg, fg=fg, activebackground=self.acento,
                    activeforeground="#FFFFFF", relief="flat", bd=0,
                    cursor="hand2", font=("Segoe UI", 9), pady=4
                ).grid(row=fila, column=col, padx=1, pady=1)

        tk.Button(
            self.interior, text="Hoy", command=lambda: self._elegir(date.today()),
            bg=self.acento_claro, fg=self.acento, activebackground=self.acento,
            activeforeground="#FFFFFF", relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 9, "bold"), pady=6
        ).pack(fill="x", pady=(8, 0))


class BuscadorAlumno(tk.Frame):
    """Campo con buscador: escribes y se filtran los nombres de la lista."""

    def __init__(
        self, parent, nombres, fuente=("Segoe UI", 10),
        fondo="#F8FAFC", borde="#E2E8F0", acento="#356AE6",
        acento_claro="#EAF0FF", texto="#24344D", suave="#718096",
        ipady=8, placeholder="Buscar alumno por nombre..."
    ):
        super().__init__(
            parent, bg=fondo, highlightbackground=borde,
            highlightcolor=acento, highlightthickness=1
        )
        self.nombres = list(nombres)
        self.fuente = fuente
        self.fondo = fondo
        self.borde = borde
        self.acento = acento
        self.acento_claro = acento_claro
        self.texto = texto
        self.suave = suave
        self.placeholder = placeholder
        self.placeholder_activo = False
        self.popup = None
        self.lista = None
        self.visibles = []

        self.var = tk.StringVar()
        self.entrada = tk.Entry(
            self, textvariable=self.var, font=fuente, bg=fondo, fg=texto,
            insertbackground=texto, relief="flat", bd=0, highlightthickness=0
        )
        self.entrada.pack(
            side="left", fill="x", expand=True, padx=(10, 0), ipady=ipady
        )

        tk.Label(
            self, text="🔍", bg=fondo, fg=suave, font=("Segoe UI Emoji", 10)
        ).pack(side="right", padx=(6, 10))

        self.entrada.bind("<FocusIn>", self._al_enfocar)
        self.entrada.bind("<FocusOut>", self._al_perder_foco)
        self.entrada.bind("<KeyRelease>", self._al_teclear)
        self.entrada.bind("<Down>", lambda e: self._mover(1))
        self.entrada.bind("<Up>", lambda e: self._mover(-1))
        self.entrada.bind("<Return>", self._confirmar)
        self.entrada.bind("<Escape>", lambda e: self._cerrar_popup())
        self.bind("<Destroy>", self._al_destruir)

        self._poner_placeholder()

    def get(self):
        texto = "" if self.placeholder_activo else self.var.get().strip()
        for nombre in self.nombres:
            if nombre.casefold() == texto.casefold():
                return nombre
        return texto

    def set(self, valor):
        self._cerrar_popup()
        if valor:
            self.var.set(valor)
            self.placeholder_activo = False
            self.entrada.config(fg=self.texto)
        else:
            self.var.set("")
            self.placeholder_activo = False
            self.entrada.config(fg=self.texto)
            if self.focus_get() is not self.entrada:
                self._poner_placeholder()

    def _poner_placeholder(self):
        if not self.var.get():
            self.var.set(self.placeholder)
            self.entrada.config(fg=self.suave)
            self.placeholder_activo = True

    def _al_enfocar(self, event=None):
        if self.placeholder_activo:
            self.var.set("")
            self.entrada.config(fg=self.texto)
            self.placeholder_activo = False
        self.config(highlightbackground=self.acento)
        self._filtrar()

    def _al_perder_foco(self, event=None):
        self.after(150, self._finalizar)

    def _finalizar(self):
        try:
            self._cerrar_popup()
            self.config(highlightbackground=self.borde)
            self._poner_placeholder()
        except tk.TclError:
            pass

    def _al_destruir(self, event):
        if event.widget is self:
            self._cerrar_popup()
 
    def _al_teclear(self, event):
        if event.keysym in (
            "Down", "Up", "Return", "KP_Enter", "Escape", "Tab",
            "Left", "Right", "Home", "End", "Shift_L", "Shift_R",
            "Control_L", "Control_R"
        ):
            return
        self._filtrar()

    def _filtrar(self):
        consulta = []
        if not self.placeholder_activo:
            consulta = normalizar_texto(self.var.get()).split()
        self.visibles = [
            n for n in self.nombres
            if all(p in normalizar_texto(n) for p in consulta)
        ]
        self._mostrar_popup()

    def _mostrar_popup(self):
        if self.popup is None:
            self.popup = tk.Toplevel(self)
            self.popup.overrideredirect(True)
            self.popup.configure(bg=self.borde)
            try:
                self.popup.attributes("-topmost", True)
            except tk.TclError:
                pass
            self.lista = tk.Listbox(
                self.popup, font=self.fuente, bg="#FFFFFF", fg=self.texto,
                selectbackground=self.acento, selectforeground="#FFFFFF",
                relief="flat", bd=0, highlightthickness=0,
                activestyle="none", exportselection=False, cursor="hand2"
            )
            self.lista.pack(padx=1, pady=1, fill="both", expand=True)
            self.lista.bind("<ButtonPress-1>", self._clic_lista)
            self.lista.bind("<Motion>", self._mover_raton)

        self.lista.delete(0, "end")
        if self.visibles:
            for nombre in self.visibles:
                self.lista.insert("end", "  " + nombre)
            self.lista.selection_set(0)
            self.lista.config(fg=self.texto)
        else:
            self.lista.insert("end", "  Sin resultados")
            self.lista.config(fg=self.suave)

        self.lista.config(height=min(max(len(self.visibles), 1), 6))
        self.update_idletasks()
        self.popup.update_idletasks()
        ancho = self.winfo_width()
        alto = self.lista.winfo_reqheight() + 2
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        self.popup.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _cerrar_popup(self):
        if self.popup is not None:
            try:
                self.popup.destroy()
            except tk.TclError:
                pass
        self.popup = None
        self.lista = None

    def _seleccionar(self, nombre):
        self.var.set(nombre)
        self.placeholder_activo = False
        self.entrada.config(fg=self.texto)
        self._cerrar_popup()
        self.entrada.icursor("end")

    def _clic_lista(self, event):
        indice = self.lista.nearest(event.y)
        if 0 <= indice < len(self.visibles):
            self._seleccionar(self.visibles[indice])
        return "break"

    def _mover_raton(self, event):
        if not self.visibles:
            return
        indice = self.lista.nearest(event.y)
        self.lista.selection_clear(0, "end")
        self.lista.selection_set(indice)

    def _mover(self, delta):
        if self.popup is None:
            self._filtrar()
            return "break"
        if not self.visibles:
            return "break"
        actual = self.lista.curselection()
        indice = (actual[0] if actual else -1) + delta
        indice = max(0, min(len(self.visibles) - 1, indice))
        self.lista.selection_clear(0, "end")
        self.lista.selection_set(indice)
        self.lista.see(indice)
        return "break"

    def _confirmar(self, event=None):
        if self.popup is not None and self.visibles:
            actual = self.lista.curselection()
            self._seleccionar(self.visibles[actual[0] if actual else 0])
        return "break"


def abrir_panel_director(root):
    LATERAL = "#0F243E"
    SEL = "#1E3A5F"
    FONDO = "#F1F5F9"
    BLANCO = "#FFFFFF"
    BORDE = "#E2E8F0"
    TEXTO = "#0F172A"
    SUAVE = "#64748B"
    AZUL = "#2563EB"

    DOC_LATERAL = "#10243E"
    DOC_LATERAL_CLARO = "#1C3555"
    DOC_AZUL = "#3478F6"
    DOC_AZUL_OSCURO = "#2359C4"
    DOC_AZUL_CLARO = "#E8F0FF"
    DOC_FONDO = "#F3F6FB"
    DOC_BLANCO = "#FFFFFF"
    DOC_TEXTO = "#172B4D"
    DOC_GRIS = "#718096"
    DOC_BORDE = "#E1E8F0"
    DOC_VERDE = "#15966A"
    DOC_VERDE_CLARO = "#E0F7ED"

    DIRECTOR = {
        "nombre": "Roberto Hernandez Silva",
        "puesto": "Director del plantel",
        "numero": "DIR-001",
        "estado": "En servicio",
        "correo": "director@plantel.edu.mx",
        "telefono": "55 8765 4321",
        "plantel": "Primaria Nezahualcoyotl",
        "area": "Dirección escolar",
        "ingreso": "15/08/2020"
    }

    ALUMNOS = [
        "Ana López Martínez",
        "Carlos Hernández Ruiz",
        "Sofía García Torres",
        "Diego Ramírez Flores",
        "Valeria Sánchez Cruz",
        "Mateo Flores Díaz",
        "Camila Torres Reyes",
        "Emiliano Cruz Morales",
        "Daniela Ruiz López",
        "Sebastián Morales Vega"
    ]

    GRUPOS = ["1° A", "2° A", "3° A", "4° A", "5° A", "6° A"]

    GRUPOS_ALUMNOS = {
        "1° A": ["Ana López Martínez", "Carlos Hernández Ruiz"],
        "2° A": ["Valeria Sánchez Cruz", "Mateo Flores Díaz"],
        "3° A": ["Camila Torres Reyes", "Emiliano Cruz Morales"],
        "4° A": ["Sofía García Torres", "Diego Ramírez Flores"],
        "5° A": ["Daniela Ruiz López", "Sebastián Morales Vega"],
        "6° A": []
    }

    DOCENTES = [
        {
            "numero": "EMP-001",
            "nombre": "Ana Torres López",
            "puesto": "Docente de primaria",
            "grado": "1° A",
            "entrada": "07:35 a. m.",
            "salida": "02:00 p. m.",
            "telefono": "55 0000 0001",
            "emergencia": "55 0000 0011",
            "contacto": "Familiar",
            "seguro": "IMSS",
            "ingreso": "15/08/2023",
            "estado": "En servicio"
        },
        {
            "numero": "EMP-002",
            "nombre": "Carlos Méndez Ruiz",
            "puesto": "Docente de primaria",
            "grado": "2° A",
            "entrada": "07:30 a. m.",
            "salida": "02:00 p. m.",
            "telefono": "55 0000 0002",
            "emergencia": "55 0000 0012",
            "contacto": "Familiar",
            "seguro": "IMSS",
            "ingreso": "10/01/2022",
            "estado": "En servicio"
        },
        {
            "numero": "EMP-003",
            "nombre": "Laura Sánchez Pérez",
            "puesto": "Docente de primaria",
            "grado": "3° A",
            "entrada": "07:40 a. m.",
            "salida": "02:00 p. m.",
            "telefono": "55 0000 0003",
            "emergencia": "55 0000 0013",
            "contacto": "Familiar",
            "seguro": "ISSSTE",
            "ingreso": "20/08/2021",
            "estado": "En servicio"
        },
        {
            "numero": "EMP-004",
            "nombre": "Jorge Ramírez Soto",
            "puesto": "Docente de primaria",
            "grado": "4° A",
            "entrada": "07:30 a. m.",
            "salida": "02:00 p. m.",
            "telefono": "55 0000 0004",
            "emergencia": "55 0000 0014",
            "contacto": "Familiar",
            "seguro": "IMSS",
            "ingreso": "12/08/2020",
            "estado": "En servicio"
        },
        {
            "numero": "EMP-005",
            "nombre": "María Flores Díaz",
            "puesto": "Docente de primaria",
            "grado": "5° A",
            "entrada": "07:35 a. m.",
            "salida": "02:00 p. m.",
            "telefono": "55 0000 0005",
            "emergencia": "55 0000 0015",
            "contacto": "Familiar",
            "seguro": "ISSSTE",
            "ingreso": "05/01/2024",
            "estado": "En servicio"
        },
        {
            "numero": "EMP-006",
            "nombre": "Roberto Cruz Vega",
            "puesto": "Docente de primaria",
            "grado": "6° A",
            "entrada": "07:45 a. m.",
            "salida": "02:00 p. m.",
            "telefono": "55 0000 0006",
            "emergencia": "55 0000 0016",
            "contacto": "Familiar",
            "seguro": "IMSS",
            "ingreso": "18/08/2022",
            "estado": "En servicio"
        }
    ]

    root.title("Plantel Educativo - Primaria Nezahualcoyotl")
    root.geometry("1150x680")
    root.minsize(620, 430)
    root.resizable(True, True)
    root.configure(bg=FONDO)
    root.state("zoomed")

    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "Treeview",
        rowheight=34,
        font=("Arial", 10),
        background=BLANCO,
        fieldbackground=BLANCO,
        borderwidth=0,
        foreground=TEXTO
    )

    style.configure(
        "Treeview.Heading",
        font=("Arial", 9, "bold"),
        background="#F8FAFC",
        foreground=SUAVE
    )

    style.configure(
        "TCombobox",
        fieldbackground=BLANCO,
        background=BLANCO,
        foreground=DOC_TEXTO,
        padding=7
    )

    style.map("TCombobox", fieldbackground=[("readonly", BLANCO)])

    def crear_app():
        for widget in root.winfo_children():
            widget.destroy()

        sidebar = tk.Frame(root, bg=LATERAL, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        def ajustar_ancho_director(event=None):
            ancho_ventana = root.winfo_width()
            sidebar.config(width=145 if ancho_ventana < 700 else (165 if ancho_ventana < 900 else 200))

        root.bind("<Configure>", ajustar_ancho_director, add="+")

        main = tk.Frame(root, bg=FONDO)
        main.pack(side="left", fill="both", expand=True)

        header = tk.Frame(
            main, bg=BLANCO, height=50,
            highlightbackground=BORDE, highlightthickness=1
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        body = tk.Frame(main, bg=FONDO)
        body.pack(fill="both", expand=True)

        lienzo_activo = None

        def desplazar_rueda(event):
            desplazar_contenido_con_rueda(event, lienzo_activo)
            return "break"

        def desplazar_linux_arriba(event):
            desplazar_contenido_con_rueda(event, lienzo_activo)
            return "break"

        def desplazar_linux_abajo(event):
            desplazar_contenido_con_rueda(event, lienzo_activo)
            return "break"

        root.bind_all("<MouseWheel>", desplazar_rueda)
        root.bind_all("<Button-4>", desplazar_linux_arriba)
        root.bind_all("<Button-5>", desplazar_linux_abajo)

        def limpiar_body(titulo):
            nonlocal lienzo_activo
            lienzo_activo = None

            for widget in body.winfo_children():
                widget.destroy()

            for widget in header.winfo_children():
                widget.destroy()

            tk.Label(
                header, text=titulo, font=("Arial", 13, "bold"),
                bg=BLANCO, fg=TEXTO
            ).pack(side="left", padx=20, pady=12)

        def crear_area_desplazable(parent, fondo=FONDO):
            nonlocal lienzo_activo

            zona = tk.Frame(parent, bg=fondo)
            zona.pack(fill="both", expand=True)

            lienzo = tk.Canvas(
                zona, bg=fondo, highlightthickness=0, borderwidth=0
            )
            barra = ttk.Scrollbar(
                zona, orient="vertical", command=lienzo.yview
            )
            lienzo.configure(yscrollcommand=barra.set)
            barra.pack(side="right", fill="y")
            lienzo.pack(side="left", fill="both", expand=True)

            contenido = tk.Frame(lienzo, bg=fondo)
            ventana_canvas = lienzo.create_window(
                (0, 0), window=contenido, anchor="nw"
            )

            estado_barra = {"visible": True, "pendiente": False}

            def revisar_barra():
                estado_barra["pendiente"] = False
                try:
                    if not lienzo.winfo_exists():
                        return
                    necesita = (
                        contenido.winfo_reqheight() > lienzo.winfo_height() > 1
                    )
                except tk.TclError:
                    return
                if necesita and not estado_barra["visible"]:
                    barra.pack(side="right", fill="y", before=lienzo)
                    estado_barra["visible"] = True
                elif not necesita and estado_barra["visible"]:
                    barra.pack_forget()
                    estado_barra["visible"] = False

            def actualizar_region(event=None):
                lienzo.configure(scrollregion=lienzo.bbox("all"))
                if not estado_barra["pendiente"]:
                    estado_barra["pendiente"] = True
                    lienzo.after_idle(revisar_barra)

            def ajustar_lienzo(event):
                lienzo.itemconfigure(ventana_canvas, width=event.width)
                actualizar_region()

            contenido.bind("<Configure>", actualizar_region)
            lienzo.bind("<Configure>", ajustar_lienzo)

            lienzo_activo = lienzo
            return lienzo, contenido

        def obtener_iniciales(nombre):
            palabras = nombre.split()
            return "".join(p[0] for p in palabras[:2]).upper()

        def crear_dato(parent, nombre, valor, fila, columna):
            bloque = tk.Frame(parent, bg=DOC_BLANCO)
            bloque.grid(
                row=fila, column=columna, sticky="nsew",
                padx=10, pady=9
            )

            tk.Label(
                bloque, text=nombre.upper(), bg=DOC_BLANCO,
                fg=DOC_GRIS, font=("Arial", 8, "bold"), anchor="w"
            ).pack(anchor="w")

            tk.Label(
                bloque, text=valor, bg=DOC_BLANCO,
                fg=DOC_TEXTO, font=("Arial", 10, "bold"),
                wraplength=300, justify="left", anchor="w"
            ).pack(anchor="w", pady=(5, 0))

        def crear_seccion(parent, titulo, subtitulo):
            tarjeta = tk.Frame(
                parent, bg=DOC_BLANCO,
                highlightbackground=DOC_BORDE, highlightthickness=1
            )
            tarjeta.pack(fill="x", padx=18, pady=(0, 13))

            tk.Label(
                tarjeta, text=titulo, bg=DOC_BLANCO,
                fg=DOC_TEXTO, font=("Arial", 12, "bold")
            ).pack(anchor="w", padx=16, pady=(13, 2))

            tk.Label(
                tarjeta, text=subtitulo, bg=DOC_BLANCO,
                fg=DOC_GRIS, font=("Arial", 9),
                wraplength=650, justify="left"
            ).pack(anchor="w", padx=16, pady=(0, 10))

            tk.Frame(tarjeta, bg=DOC_BORDE, height=1).pack(
                fill="x", padx=15
            )

            cuerpo = tk.Frame(tarjeta, bg=DOC_BLANCO)
            cuerpo.pack(fill="x", padx=5, pady=5)
            cuerpo.grid_columnconfigure(0, weight=1)
            cuerpo.grid_columnconfigure(1, weight=1)
            return cuerpo

        def crear_boton_docente(parent, texto, comando):
            return tk.Button(
                parent, text=texto, command=comando,
                bg=DOC_AZUL, fg=DOC_BLANCO,
                activebackground=DOC_AZUL_OSCURO,
                activeforeground=DOC_BLANCO,
                font=("Arial", 8, "bold"), relief="flat",
                cursor="hand2", padx=7, pady=5, bd=0
            )


        def crear_tarjeta_grafica(parent, titulo, subtitulo, alto, dibujar):
            tarjeta_g = tk.Frame(
                parent, bg=BLANCO,
                highlightbackground=BORDE, highlightthickness=1
            )

            tk.Label(
                tarjeta_g, text=titulo, font=("Arial", 11, "bold"),
                bg=BLANCO, fg=DOC_TEXTO, anchor="w"
            ).pack(anchor="w", padx=16, pady=(14, 2))

            tk.Label(
                tarjeta_g, text=subtitulo, font=("Arial", 8),
                bg=BLANCO, fg=DOC_GRIS, anchor="w"
            ).pack(anchor="w", padx=16, pady=(0, 8))

            lienzo_g = tk.Canvas(
                tarjeta_g, height=alto, bg=BLANCO,
                highlightthickness=0, bd=0
            )
            lienzo_g.pack(fill="x", padx=12, pady=(0, 12))

            def redibujar(event):
                lienzo_g.delete("all")
                if event.width > 80:
                    dibujar(lienzo_g, event.width, alto)

            lienzo_g.bind("<Configure>", redibujar)
            return tarjeta_g

        def dibujar_barras(c, w, h):
            datos = [
                ("1° A", 96), ("2° A", 93), ("3° A", 91),
                ("4° A", 95), ("5° A", 89), ("6° A", 94)
            ]
            izq, der, arr, aba = 34, 10, 16, 26
            ancho_u = w - izq - der
            alto_u = h - arr - aba

            for valor in (0, 25, 50, 75, 100):
                y = arr + alto_u - alto_u * valor / 100
                c.create_line(izq, y, w - der, y, fill="#E8EDF3")
                c.create_text(
                    izq - 6, y, text=str(valor), anchor="e",
                    font=("Arial", 8), fill=DOC_GRIS
                )

            paso = ancho_u / len(datos)
            ancho_b = min(46, paso * 0.55)
            base = arr + alto_u

            for i, (grupo, valor) in enumerate(datos):
                x0 = izq + paso * i + (paso - ancho_b) / 2
                x1 = x0 + ancho_b
                y0 = base - alto_u * valor / 100
                c.create_rectangle(x0, y0, x1, base, fill="#2563EB", outline="")
                c.create_text(
                    (x0 + x1) / 2, y0 - 8, text=f"{valor}%",
                    font=("Arial", 8, "bold"), fill=DOC_TEXTO
                )
                c.create_text(
                    (x0 + x1) / 2, base + 13, text=grupo,
                    font=("Arial", 9), fill=DOC_GRIS
                )

        def dibujar_dona(c, w, h):
            partes = [
                ("Asistieron", 135, "#16A34A"),
                ("Retardos", 7, "#CA8A04"),
                ("Faltas", 8, "#E11D48")
            ]
            total = sum(v for _, v, _ in partes)
            r = max(28, min(h / 2 - 8, (w - 150) / 2))
            grosor = max(12, r * 0.32)
            cx, cy = r + 14, h / 2
            caja = (
                cx - r + grosor / 2, cy - r + grosor / 2,
                cx + r - grosor / 2, cy + r - grosor / 2
            )

            inicio = 90
            for _, valor, color in partes:
                barrido = 360 * valor / total
                c.create_arc(
                    *caja, start=inicio, extent=-barrido, style="arc",
                    outline=color, width=grosor
                )
                inicio -= barrido

            c.create_text(
                cx, cy - 7, text=str(total),
                font=("Arial", 17, "bold"), fill=DOC_TEXTO
            )
            c.create_text(
                cx, cy + 12, text="alumnos",
                font=("Arial", 8), fill=DOC_GRIS
            )

            lx = cx + r + 24
            for i, (nombre, valor, color) in enumerate(partes):
                y = cy - 34 + i * 34
                c.create_rectangle(lx, y - 5, lx + 10, y + 5, fill=color, outline="")
                c.create_text(
                    lx + 18, y, text=nombre, anchor="w",
                    font=("Arial", 9, "bold"), fill=DOC_TEXTO
                )
                c.create_text(
                    lx + 18, y + 14, text=f"{valor} alumnos", anchor="w",
                    font=("Arial", 8), fill=DOC_GRIS
                )

        def dibujar_hbarras(c, w, h):
            datos = [
                ("Conducta", 9), ("Académico", 6),
                ("Incidente", 3), ("Otro", 2)
            ]
            izq, der = 80, 40
            maximo = max(v for _, v in datos)
            paso = h / len(datos)

            for i, (nombre, valor) in enumerate(datos):
                cy = paso * i + paso / 2
                largo = (w - izq - der) * valor / maximo
                c.create_text(
                    izq - 10, cy, text=nombre, anchor="e",
                    font=("Arial", 9), fill=DOC_GRIS
                )
                c.create_rectangle(
                    izq, cy - 9, izq + largo, cy + 9,
                    fill="#9333EA", outline=""
                )
                c.create_text(
                    izq + largo + 8, cy, text=str(valor), anchor="w",
                    font=("Arial", 9, "bold"), fill=DOC_TEXTO
                )

        def dibujar_linea(c, w, h):
            datos = [
                ("Lun", 94), ("Mar", 92), ("Mié", 95),
                ("Jue", 90), ("Vie", 93)
            ]
            izq, der, arr, aba = 34, 14, 16, 26
            minimo, maximo = 80, 100
            ancho_u = w - izq - der
            alto_u = h - arr - aba

            for valor in (80, 85, 90, 95, 100):
                y = arr + alto_u - alto_u * (valor - minimo) / (maximo - minimo)
                c.create_line(izq, y, w - der, y, fill="#E8EDF3")
                c.create_text(
                    izq - 6, y, text=str(valor), anchor="e",
                    font=("Arial", 8), fill=DOC_GRIS
                )

            puntos = []
            for i, (dia, valor) in enumerate(datos):
                x = izq + ancho_u * (i + 0.5) / len(datos)
                y = arr + alto_u - alto_u * (valor - minimo) / (maximo - minimo)
                puntos.append((x, y, dia, valor))

            coordenadas = [n for x, y, _, _ in puntos for n in (x, y)]
            c.create_line(*coordenadas, fill="#0D9488", width=3)

            for x, y, dia, valor in puntos:
                c.create_oval(
                    x - 5, y - 5, x + 5, y + 5,
                    fill="#FFFFFF", outline="#0D9488", width=2
                )
                c.create_text(
                    x, y - 14, text=f"{valor}%",
                    font=("Arial", 8, "bold"), fill=DOC_TEXTO
                )
                c.create_text(
                    x, arr + alto_u + 13, text=dia,
                    font=("Arial", 9), fill=DOC_GRIS
                )


        def pantalla_inicio():
            limpiar_body("Bienvenido, Director de la Primaria Nezahualcoyotl")
            lienzo, cont = crear_area_desplazable(body, FONDO)

            tk.Label(
                cont,
                text="Resumen general",
                font=("Arial", 20, "bold"),
                bg=FONDO,
                fg=DOC_TEXTO
            ).pack(anchor="w", padx=18, pady=(18, 4))

            tk.Label(
                cont,
                text="Consulta los indicadores principales del plantel.",
                font=("Arial", 10),
                bg=FONDO,
                fg=DOC_GRIS
            ).pack(anchor="w", padx=18, pady=(0, 16))

            tarjetas = [
                ("Total docentes", "6", "#2563EB", "Personal del plantel"),
                ("Total grupos", "6", "#16A34A", "Grupos registrados"),
                ("Total alumnos", "150", "#9333EA", "Alumnos inscritos"),
                ("Cartas compromiso", "12", "#CA8A04", "Cartas registradas"),
                ("Justificantes", "8", "#E11D48", "Justificantes recibidos"),
                ("Asistencias hoy", "142 / 150", "#0D9488", "Registro de asistencia")
            ]

            cuadrilla = tk.Frame(cont, bg=FONDO)
            cuadrilla.pack(fill="x", padx=18, pady=(0, 16))

            for columna in range(3):
                cuadrilla.grid_columnconfigure(columna, weight=1, uniform="tarjetas")

            for indice, (nombre, valor, color, detalle) in enumerate(tarjetas):
                fila = indice // 3
                columna = indice % 3

                tarjeta = tk.Frame(
                    cuadrilla,
                    bg=BLANCO,
                    highlightbackground=BORDE,
                    highlightthickness=1,
                    padx=15,
                    pady=14
                )
                tarjeta.grid(
                    row=fila,
                    column=columna,
                    sticky="nsew",
                    padx=(0 if columna == 0 else 6, 0 if columna == 2 else 6),
                    pady=6
                )

                tk.Frame(
                    tarjeta,
                    bg=color,
                    height=4
                ).pack(fill="x", pady=(0, 13))

                tk.Label(
                    tarjeta,
                    text=nombre.upper(),
                    font=("Arial", 9, "bold"),
                    bg=BLANCO,
                    fg=DOC_GRIS,
                    anchor="w"
                ).pack(anchor="w")

                tk.Label(
                    tarjeta,
                    text=valor,
                    font=("Arial", 23, "bold"),
                    bg=BLANCO,
                    fg=DOC_TEXTO,
                    anchor="w"
                ).pack(anchor="w", pady=(6, 2))

                tk.Label(
                    tarjeta,
                    text=detalle,
                    font=("Arial", 8),
                    bg=BLANCO,
                    fg=DOC_GRIS,
                    anchor="w",
                    wraplength=200,
                    justify="left"
                ).pack(anchor="w")

            tk.Label(
                cont,
                text="Gráficas",
                font=("Arial", 14, "bold"),
                bg=FONDO,
                fg=DOC_TEXTO
            ).pack(anchor="w", padx=18, pady=(4, 2))

            tk.Label(
                cont,
                text="Resumen visual de asistencias e incidencias (datos de demostración).",
                font=("Arial", 9),
                bg=FONDO,
                fg=DOC_GRIS
            ).pack(anchor="w", padx=18, pady=(0, 8))

            zona_graficas = tk.Frame(cont, bg=FONDO)
            zona_graficas.pack(fill="x", padx=18, pady=(0, 10))
            zona_graficas.grid_columnconfigure(0, weight=3, uniform="graf")
            zona_graficas.grid_columnconfigure(1, weight=2, uniform="graf")

            crear_tarjeta_grafica(
                zona_graficas, "Asistencia por grupo",
                "Porcentaje promedio de asistencia del mes", 200,
                dibujar_barras
            ).grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=6)

            crear_tarjeta_grafica(
                zona_graficas, "Asistencia de hoy",
                "Estado de los alumnos inscritos", 200, dibujar_dona
            ).grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=6)

            crear_tarjeta_grafica(
                zona_graficas, "Incidencias por tipo",
                "Total registrado en el mes", 160, dibujar_hbarras
            ).grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=6)

            crear_tarjeta_grafica(
                zona_graficas, "Asistencia semanal",
                "Porcentaje de la semana actual", 160, dibujar_linea
            ).grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=6)

            box = tk.Frame(
                cont,
                bg=BLANCO,
                highlightbackground=BORDE,
                highlightthickness=1
            )
            box.pack(fill="x", padx=18, pady=(0, 15))

            inner2 = tk.Frame(box, bg=BLANCO, padx=18, pady=15)
            inner2.pack(fill="x")

            tk.Label(
                inner2,
                text="Últimas actividades",
                font=("Arial", 12, "bold"),
                bg=BLANCO,
                fg=DOC_TEXTO,
                anchor="w"
            ).pack(anchor="w", pady=(0, 8))

            actividades = [
                "28/09 - Carta compromiso Juan Perez 2A",
                "28/09 - Justificante Ana Lopez 1B",
                "27/09 - Asistencia 3A actualizada",
                "27/09 - Nuevo docente Carlos Mendez"
            ]

            for actividad in actividades:
                tk.Label(
                    inner2,
                    text="• " + actividad,
                    font=("Arial", 9),
                    bg=BLANCO,
                    fg=DOC_TEXTO,
                    anchor="w",
                    wraplength=700,
                    justify="left"
                ).pack(anchor="w", pady=3, fill="x")


        def pantalla_docentes():
            limpiar_body("Docentes - 6 docentes")
            lienzo, contenido = crear_area_desplazable(body, DOC_FONDO)

            tk.Label(
                contenido, text="GESTIÓN ESCOLAR  /  PERSONAL",
                bg=DOC_FONDO, fg=DOC_AZUL,
                font=("Arial", 8, "bold")
            ).pack(anchor="w", padx=22, pady=(19, 5))

            tk.Label(
                contenido, text="Personal docente",
                bg=DOC_FONDO, fg=DOC_TEXTO,
                font=("Arial", 21, "bold")
            ).pack(anchor="w", padx=22)

            tk.Label(
                contenido,
                text="Administra y consulta la información de tus maestros.",
                bg=DOC_FONDO, fg=DOC_GRIS, font=("Arial", 10),
                wraplength=650, justify="left"
            ).pack(anchor="w", padx=22, pady=(4, 15))

            banner = tk.Frame(contenido, bg=DOC_LATERAL)
            banner.pack(fill="x", padx=18, pady=(0, 15))
            banner.grid_columnconfigure(0, weight=1)

            texto_banner = tk.Frame(banner, bg=DOC_LATERAL)
            texto_banner.grid(row=0, column=0, sticky="w", padx=18, pady=17)

            tk.Label(
                texto_banner, text="DIRECTORIO DEL PLANTEL",
                bg=DOC_LATERAL, fg="#9DB9E0",
                font=("Arial", 8, "bold")
            ).pack(anchor="w")

            tk.Label(
                texto_banner, text="Equipo docente",
                bg=DOC_LATERAL, fg=DOC_BLANCO,
                font=("Arial", 17, "bold")
            ).pack(anchor="w", pady=(4, 3))

            tk.Label(
                texto_banner, text="Consulta los datos de cada integrante.",
                bg=DOC_LATERAL, fg="#D0DCEC", font=("Arial", 9),
                wraplength=300, justify="left"
            ).pack(anchor="w")

            contador = tk.Frame(
                banner, bg=DOC_LATERAL_CLARO,
                highlightbackground="#3B5778", highlightthickness=1
            )
            contador.grid(row=0, column=1, padx=16, pady=14)

            tk.Label(
                contador, text=str(len(DOCENTES)),
                bg=DOC_LATERAL_CLARO, fg=DOC_BLANCO,
                font=("Arial", 23, "bold")
            ).pack(padx=20, pady=(10, 0))

            tk.Label(
                contador, text="DOCENTES",
                bg=DOC_LATERAL_CLARO, fg="#C5D5E8",
                font=("Arial", 8, "bold")
            ).pack(padx=12, pady=(0, 10))

            zona_lista = tk.Frame(contenido, bg=DOC_FONDO)
            zona_lista.pack(fill="x", padx=18, pady=(0, 6))

            tk.Label(
                zona_lista, text="Directorio de maestros",
                bg=DOC_FONDO, fg=DOC_TEXTO,
                font=("Arial", 12, "bold")
            ).pack(side="left")

            tk.Label(
                zona_lista, text="REGISTRO ACTUAL",
                bg=DOC_AZUL_CLARO, fg=DOC_AZUL_OSCURO,
                font=("Arial", 8, "bold"), padx=8, pady=4
            ).pack(side="right")

            tabla = tk.Frame(contenido, bg=DOC_FONDO)
            tabla.pack(fill="x", padx=18, pady=(0, 15))

            def configurar_columnas(fila):
                fila.grid_columnconfigure(0, weight=5, minsize=120)
                fila.grid_columnconfigure(1, weight=1, minsize=45)
                fila.grid_columnconfigure(2, weight=2, minsize=85)
                fila.grid_columnconfigure(3, weight=0, minsize=70)

            cabecera = tk.Frame(tabla, bg="#E5ECF6")
            cabecera.pack(fill="x", pady=(0, 4))
            configurar_columnas(cabecera)

            for texto, columna in [
                ("DOCENTE", 0), ("GRUPO", 1), ("ENTRADA", 2), ("", 3)
            ]:
                tk.Label(
                    cabecera, text=texto, bg="#E5ECF6", fg=DOC_GRIS,
                    font=("Arial", 8, "bold"),
                    anchor="w" if columna == 0 else "center",
                    padx=8, pady=10
                ).grid(row=0, column=columna, sticky="nsew")

            colores_avatar = [
                ("#E4ECFF", DOC_AZUL_OSCURO),
                ("#DDF6ED", DOC_VERDE),
                ("#FDE8D7", "#C05B22"),
                ("#F0E5FF", "#7951B3"),
                ("#DDF3F8", "#167A91"),
                ("#FCE7F3", "#B83280")
            ]

            for indice, docente in enumerate(DOCENTES):
                fila = tk.Frame(
                    tabla, bg=DOC_BLANCO,
                    highlightbackground=DOC_BORDE, highlightthickness=1
                )
                fila.pack(fill="x", pady=2)
                configurar_columnas(fila)

                fondo_avatar, texto_avatar = colores_avatar[indice % 6]

                datos_nombre = tk.Frame(fila, bg=DOC_BLANCO)
                datos_nombre.grid(
                    row=0, column=0, sticky="nsew", padx=8, pady=8
                )

                tk.Label(
                    datos_nombre, text=obtener_iniciales(docente["nombre"]),
                    bg=fondo_avatar, fg=texto_avatar,
                    font=("Arial", 9, "bold"), width=3, pady=7
                ).pack(side="left", padx=(0, 8))

                textos = tk.Frame(datos_nombre, bg=DOC_BLANCO)
                textos.pack(side="left", fill="x", expand=True)

                tk.Label(
                    textos, text=docente["nombre"],
                    bg=DOC_BLANCO, fg=DOC_TEXTO,
                    font=("Arial", 9, "bold"), anchor="w",
                    wraplength=210, justify="left"
                ).pack(anchor="w")

                tk.Label(
                    textos, text=docente["puesto"],
                    bg=DOC_BLANCO, fg=DOC_GRIS,
                    font=("Arial", 8), anchor="w"
                ).pack(anchor="w", pady=(2, 0))

                tk.Label(
                    fila, text=docente["grado"],
                    bg=DOC_AZUL_CLARO, fg=DOC_AZUL_OSCURO,
                    font=("Arial", 8, "bold"), padx=5, pady=4
                ).grid(row=0, column=1, padx=3, pady=8, sticky="n")

                tk.Label(
                    fila, text=docente["entrada"],
                    bg=DOC_BLANCO, fg=DOC_GRIS,
                    font=("Arial", 8), anchor="center"
                ).grid(row=0, column=2, sticky="nsew", padx=2, pady=8)

                crear_boton_docente(
                    fila, "Ver perfil",
                    lambda d=docente: mostrar_perfil_docente(d)
                ).grid(row=0, column=3, padx=5, pady=8, sticky="ew")

            tk.Label(
                contenido, text="Sistema de administración escolar",
                bg=DOC_FONDO, fg=DOC_GRIS, font=("Arial", 8)
            ).pack(anchor="w", padx=22, pady=(0, 15))


        def mostrar_perfil_docente(perfil):
            limpiar_body("Perfil del docente")
            lienzo, contenido = crear_area_desplazable(body, DOC_FONDO)

            tk.Label(
                contenido, text="GESTIÓN ESCOLAR  /  PERFIL",
                bg=DOC_FONDO, fg=DOC_AZUL,
                font=("Arial", 8, "bold")
            ).pack(anchor="w", padx=22, pady=(18, 5))

            crear_boton_docente(
                contenido, "‹  Volver al directorio", pantalla_docentes
            ).pack(anchor="w", padx=18, pady=(0, 12))

            cabecera = tk.Frame(contenido, bg=DOC_LATERAL)
            cabecera.pack(fill="x", padx=18, pady=(0, 14))
            cabecera.grid_columnconfigure(1, weight=1)

            tk.Label(
                cabecera, text=obtener_iniciales(perfil["nombre"]),
                bg=DOC_AZUL, fg=DOC_BLANCO,
                font=("Arial", 20, "bold"), width=4, pady=12
            ).grid(row=0, column=0, padx=16, pady=17)

            datos = tk.Frame(cabecera, bg=DOC_LATERAL)
            datos.grid(row=0, column=1, sticky="nsew", pady=17)

            tk.Label(
                datos, text=perfil["nombre"], bg=DOC_LATERAL,
                fg=DOC_BLANCO, font=("Arial", 15, "bold"),
                wraplength=350, justify="left"
            ).pack(anchor="w")

            tk.Label(
                datos, text=perfil["puesto"], bg=DOC_LATERAL,
                fg="#C5D5E8", font=("Arial", 9)
            ).pack(anchor="w", pady=(4, 6))

            tk.Label(
                datos, text="Número de empleado: " + perfil["numero"],
                bg=DOC_LATERAL, fg="#9DB9E0", font=("Arial", 9)
            ).pack(anchor="w")

            tk.Label(
                cabecera, text="● " + perfil["estado"],
                bg=DOC_VERDE_CLARO, fg=DOC_VERDE,
                font=("Arial", 8, "bold"), padx=8, pady=6
            ).grid(row=0, column=2, padx=13, pady=14, sticky="ne")

            laboral = crear_seccion(
                contenido, "Información laboral",
                "Datos relacionados con las actividades del docente."
            )

            crear_dato(laboral, "Grado y grupo", perfil["grado"], 0, 0)
            crear_dato(laboral, "Fecha de ingreso", perfil["ingreso"], 0, 1)
            crear_dato(laboral, "Hora de entrada", perfil["entrada"], 1, 0)
            crear_dato(laboral, "Hora de salida", perfil["salida"], 1, 1)

            contacto = crear_seccion(
                contenido, "Contacto y emergencia",
                "Información para comunicación y situaciones de emergencia."
            )

            crear_dato(contacto, "Teléfono del docente", perfil["telefono"], 0, 0)
            crear_dato(contacto, "Teléfono de emergencia", perfil["emergencia"], 0, 1)
            crear_dato(contacto, "Relación del contacto", perfil["contacto"], 1, 0)
            crear_dato(contacto, "Afiliación médica", perfil["seguro"], 1, 1)

            tk.Label(
                contenido, text="CONTROL ESCOLAR  •  Datos de demostración",
                bg=DOC_FONDO, fg=DOC_GRIS, font=("Arial", 8)
            ).pack(anchor="w", padx=22, pady=(0, 15))


        def pantalla_asistencias():
            limpiar_body("Registro de asistencias - 1A")
            lienzo, cont = crear_area_desplazable(body, FONDO)

            inner = tk.Frame(cont, bg=BLANCO)
            inner.pack(fill="x", expand=True, padx=15, pady=10)

            columnas = ("No", "Matricula", "Nombre", "Asis", "Ret", "Falta")
            tabla = ttk.Treeview(
                inner, columns=columnas, show="headings", height=14
            )

            for columna in columnas:
                tabla.heading(columna, text=columna)
                tabla.column(
                    columna, width=70 if columna != "Nombre" else 200,
                    anchor="center", stretch=True
                )

            tabla.pack(fill="both", expand=True, padx=10, pady=10)

            for i in range(1, 11):
                tabla.insert(
                    "", "end",
                    values=(
                        i, f"A00{i}", f"Alumno {i} Perez",
                        "X" if i != 6 else "", 1 if i == 3 else 0,
                        1 if i == 6 else 0
                    )
                )


        def pantalla_cartas():
            limpiar_body("Generar carta compromiso")
            lienzo, contenido = crear_area_desplazable(body, DOC_FONDO)

            carta_generada = ""
            grupo_var = tk.StringVar()
            tutor_var = tk.StringVar()

            tk.Label(
                contenido, text="GESTIÓN ESCOLAR  /  DOCUMENTACIÓN",
                bg=DOC_FONDO, fg=DOC_AZUL,
                font=("Arial", 8, "bold")
            ).pack(anchor="w", padx=22, pady=(19, 5))

            tk.Label(
                contenido, text="Carta compromiso",
                bg=DOC_FONDO, fg=DOC_TEXTO,
                font=("Arial", 21, "bold")
            ).pack(anchor="w", padx=22)

            tk.Label(
                contenido,
                text="Completa los datos para elaborar el documento del alumno.",
                bg=DOC_FONDO, fg=DOC_GRIS, font=("Arial", 10),
                wraplength=650, justify="left"
            ).pack(anchor="w", padx=22, pady=(4, 15))

            banner = tk.Frame(contenido, bg=DOC_LATERAL)
            banner.pack(fill="x", padx=18, pady=(0, 15))
            banner.grid_columnconfigure(0, weight=1)

            texto_banner = tk.Frame(banner, bg=DOC_LATERAL)
            texto_banner.grid(row=0, column=0, sticky="w", padx=18, pady=17)

            tk.Label(
                texto_banner, text="DOCUMENTACIÓN ESCOLAR",
                bg=DOC_LATERAL, fg="#9DB9E0",
                font=("Arial", 8, "bold")
            ).pack(anchor="w")

            tk.Label(
                texto_banner, text="Nueva carta compromiso",
                bg=DOC_LATERAL, fg=DOC_BLANCO,
                font=("Arial", 17, "bold"), wraplength=350, justify="left"
            ).pack(anchor="w", pady=(4, 3))

            tk.Label(
                texto_banner,
                text="Prepara, revisa y guarda el documento del alumno.",
                bg=DOC_LATERAL, fg="#D0DCEC", font=("Arial", 9),
                wraplength=350, justify="left"
            ).pack(anchor="w")

            etiqueta = tk.Frame(
                banner, bg=DOC_LATERAL_CLARO,
                highlightbackground="#3B5778", highlightthickness=1
            )
            etiqueta.grid(row=0, column=1, padx=16, pady=14)

            tk.Label(
                etiqueta, text="NUEVO", bg=DOC_LATERAL_CLARO,
                fg=DOC_BLANCO, font=("Arial", 10, "bold")
            ).pack(padx=16, pady=15)

            formulario = crear_seccion(
                contenido, "Datos de la carta",
                "Completa los datos del alumno, tutor y acuerdos del compromiso."
            )

            def etiqueta_campo(texto, fila, columna, ancho=1):
                tk.Label(
                    formulario, text=texto.upper(), bg=DOC_BLANCO,
                    fg=DOC_GRIS, font=("Arial", 8, "bold")
                ).grid(
                    row=fila, column=columna, columnspan=ancho,
                    sticky="w", padx=10, pady=(8, 4)
                )

            def crear_entrada(variable, fila, columna):
                entrada = tk.Entry(
                    formulario, textvariable=variable, font=("Arial", 10),
                    bg="#F8FAFC", fg=DOC_TEXTO, relief="flat",
                    highlightthickness=1, highlightbackground=DOC_BORDE,
                    highlightcolor=DOC_AZUL
                )
                entrada.grid(
                    row=fila, column=columna, sticky="ew",
                    padx=10, pady=(0, 10), ipady=8
                )
                return entrada

            etiqueta_campo("Alumno", 0, 0)
            alumno = BuscadorAlumno(
                formulario, ALUMNOS, fuente=("Arial", 10),
                fondo="#F8FAFC", borde=DOC_BORDE, acento=DOC_AZUL,
                acento_claro=DOC_AZUL_CLARO, texto=DOC_TEXTO,
                suave=DOC_GRIS, ipady=8
            )
            alumno.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

            etiqueta_campo("Grupo", 0, 1)
            grupo = ttk.Combobox(
                formulario, textvariable=grupo_var, values=GRUPOS,
                state="readonly", font=("Arial", 10)
            )
            grupo.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10), ipady=5)
            grupo.set("Selecciona un grupo...")

            etiqueta_campo("Nombre del padre, madre o tutor", 2, 0)
            crear_entrada(tutor_var, 3, 0)

            etiqueta_campo("Fecha de elaboración", 2, 1)
            selector_fecha = SelectorFecha(
                formulario, fuente=("Arial", 10), fondo="#F8FAFC",
                borde=DOC_BORDE, acento=DOC_AZUL,
                acento_claro=DOC_AZUL_CLARO, texto=DOC_TEXTO,
                suave=DOC_GRIS, ipady=8
            )
            selector_fecha.grid(
                row=3, column=1, sticky="ew", padx=10, pady=(0, 10)
            )

            etiqueta_campo("Motivo del compromiso", 4, 0, 2)
            motivo_texto = tk.Text(
                formulario, height=4, font=("Arial", 10),
                bg="#F8FAFC", fg=DOC_TEXTO, relief="flat", wrap="word",
                highlightbackground=DOC_BORDE, highlightthickness=1,
                insertbackground=DOC_TEXTO
            )
            motivo_texto.grid(
                row=5, column=0, columnspan=2, sticky="ew",
                padx=10, pady=(0, 10)
            )

            etiqueta_campo("Acuerdos y compromisos", 6, 0, 2)
            acuerdos_texto = tk.Text(
                formulario, height=4, font=("Arial", 10),
                bg="#F8FAFC", fg=DOC_TEXTO, relief="flat", wrap="word",
                highlightbackground=DOC_BORDE, highlightthickness=1,
                insertbackground=DOC_TEXTO
            )
            acuerdos_texto.grid(
                row=7, column=0, columnspan=2, sticky="ew",
                padx=10, pady=(0, 15)
            )

            tk.Label(
                contenido, text="VISTA PREVIA DEL DOCUMENTO",
                bg=DOC_FONDO, fg=DOC_TEXTO,
                font=("Arial", 11, "bold")
            ).pack(anchor="w", padx=22, pady=(0, 8))

            vista = tk.Text(
                contenido, height=12, font=("Arial", 10),
                bg=DOC_BLANCO, fg=DOC_TEXTO, relief="flat",
                wrap="word", padx=16, pady=14,
                highlightbackground=DOC_BORDE, highlightthickness=1
            )
            vista.pack(fill="x", padx=18, pady=(0, 12))
            vista.insert(
                "1.0",
                "Aquí aparecerá la carta compromiso cuando completes "
                "los datos y pulses «Generar carta»."
            )
            vista.configure(state="disabled")

            def obtener_carta():
                alumno_nombre = alumno.get().strip()
                grupo_nombre = grupo_var.get().strip()
                tutor_nombre = tutor_var.get().strip()
                fecha = selector_fecha.get().strip()
                motivo = motivo_texto.get("1.0", "end").strip()
                acuerdos = acuerdos_texto.get("1.0", "end").strip()

                if (
                    not alumno_nombre
                    or alumno_nombre not in ALUMNOS
                    or not grupo_nombre
                    or grupo_nombre == "Selecciona un grupo..."
                    or not tutor_nombre or not fecha
                ):
                    messagebox.showwarning(
                        "Datos incompletos",
                        "Busca y selecciona al alumno, elige su grupo e indica "
                        "el nombre del tutor y la fecha."
                    )
                    return None

                if not motivo or not acuerdos:
                    messagebox.showwarning(
                        "Datos incompletos",
                        "Escribe el motivo y los acuerdos del compromiso."
                    )
                    return None

                return f"""PLANTEL EDUCATIVO
CARTA COMPROMISO

Fecha: {fecha}

DATOS DEL ALUMNO
Nombre: {alumno_nombre}
Grupo: {grupo_nombre}
Padre, madre o tutor: {tutor_nombre}

MOTIVO DEL COMPROMISO

{motivo}

ACUERDOS Y COMPROMISOS

{acuerdos}

Por medio de la presente, el padre, madre o tutor y el plantel
establecen los acuerdos anteriores con el propósito de apoyar
el desarrollo académico y la convivencia escolar del alumno.

Las partes manifiestan conocer el contenido de este documento
y se comprometen a dar seguimiento a los acuerdos establecidos.

____________________________
Firma del padre, madre o tutor

____________________________
Firma del docente

____________________________
Firma de la dirección

Documento elaborado para uso escolar.
"""

            def generar_carta():
                nonlocal carta_generada
                carta = obtener_carta()
                if carta is None:
                    return

                carta_generada = carta
                vista.configure(state="normal")
                vista.delete("1.0", "end")
                vista.insert("1.0", carta_generada)
                vista.configure(state="disabled")

                messagebox.showinfo(
                    "Carta generada",
                    "La carta compromiso se generó correctamente.\n"
                    "Puedes revisarla, guardarla o imprimirla."
                )

            def guardar_carta():
                if not carta_generada:
                    messagebox.showwarning(
                        "Sin documento",
                        "Primero debes generar la carta compromiso."
                    )
                    return

                ruta = filedialog.asksaveasfilename(
                    title="Guardar carta compromiso",
                    defaultextension=".txt",
                    filetypes=[
                        ("Documento de texto", "*.txt"),
                        ("Todos los archivos", "*.*")
                    ],
                    initialfile="carta_compromiso.txt"
                )

                if not ruta:
                    return

                try:
                    with open(ruta, "w", encoding="utf-8") as archivo:
                        archivo.write(carta_generada)
                    messagebox.showinfo(
                        "Documento guardado",
                        "La carta se guardó correctamente."
                    )
                except OSError as error:
                    messagebox.showerror(
                        "Error al guardar",
                        f"No se pudo guardar el documento:\n{error}"
                    )

            def imprimir_carta():
                if not carta_generada:
                    messagebox.showwarning(
                        "Sin documento",
                        "Primero debes generar la carta compromiso."
                    )
                    return

                ruta = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w", encoding="utf-8", suffix=".txt",
                        prefix="carta_compromiso_", delete=False
                    ) as archivo:
                        archivo.write(carta_generada)
                        ruta = archivo.name

                    if os.name == "nt":
                        os.startfile(ruta, "print")
                    else:
                        messagebox.showinfo(
                            "Impresión",
                            "El documento temporal se guardó. "
                            "Ábrelo con un editor de texto para imprimirlo."
                        )
                except (OSError, AttributeError) as error:
                    messagebox.showerror(
                        "No se pudo imprimir",
                        "No fue posible enviar el documento a imprimir.\n"
                        "Puedes guardarlo manualmente.\n\n"
                        f"{error}"
                    )

            acciones = tk.Frame(contenido, bg=DOC_FONDO)
            acciones.pack(fill="x", padx=18, pady=(0, 15))

            def crear_boton_carta(parent, texto, color, comando):
                return tk.Button(
                    parent, text=texto, command=comando,
                    bg=color, fg="#000000", activebackground=color,
                    activeforeground="#000000", font=("Arial", 9, "bold"),
                    relief="flat", bd=0, cursor="hand2",
                    padx=14, pady=10
                )

            crear_boton_carta(
                acciones, "Generar carta", DOC_AZUL, generar_carta
            ).pack(side="left", padx=(0, 8))

            crear_boton_carta(
                acciones, "Guardar documento", DOC_VERDE_CLARO, guardar_carta
            ).pack(side="left", padx=8)

            crear_boton_carta(
                acciones, "Imprimir", DOC_AZUL_CLARO, imprimir_carta
            ).pack(side="left", padx=8)

            tk.Label(
                contenido, text="CONTROL ESCOLAR  •  Documento de demostración",
                bg=DOC_FONDO, fg=DOC_GRIS, font=("Arial", 8)
            ).pack(anchor="w", padx=22, pady=(0, 15))


        def pantalla_justificantes():
            limpiar_body("Generar justificante")
            lienzo, cont = crear_area_desplazable(body, FONDO)

            box = tk.Frame(
                cont, bg=BLANCO, highlightbackground=BORDE,
                highlightthickness=1, padx=20, pady=20
            )
            box.pack(fill="x", padx=15, pady=15)

            tk.Label(
                box, text="Alumno", font=("Arial", 9, "bold"),
                bg=BLANCO, fg=TEXTO
            ).pack(anchor="w")

            ttk.Combobox(
                box, values=["Luis Garcia Perez", "Ana Torres Lopez"]
            ).pack(fill="x", ipady=5, pady=5)

            tk.Label(
                box, text="Descripción", font=("Arial", 9, "bold"),
                bg=BLANCO, fg=TEXTO
            ).pack(anchor="w", pady=(10, 2))

            tk.Entry(box).pack(fill="x", ipady=15, pady=5)

            tk.Button(
                box, text="Generar justificante",
                bg=AZUL, fg=BLANCO, font=("Arial", 10, "bold"),
                relief="flat", pady=10, state="disabled"
            ).pack(fill="x", pady=15)


        def pantalla_perfil():
            limpiar_body("Mi perfil")
            lienzo, contenido = crear_area_desplazable(body, DOC_FONDO)

            tk.Label(
                contenido,
                text="GESTIÓN ESCOLAR  /  PERFIL",
                bg=DOC_FONDO,
                fg=DOC_AZUL,
                font=("Arial", 8, "bold")
            ).pack(anchor="w", padx=22, pady=(18, 5))

            cabecera = tk.Frame(contenido, bg=DOC_LATERAL)
            cabecera.pack(fill="x", padx=18, pady=(0, 14))
            cabecera.grid_columnconfigure(1, weight=1)

            tk.Label(
                cabecera,
                text=obtener_iniciales(DIRECTOR["nombre"]),
                bg=DOC_AZUL,
                fg=DOC_BLANCO,
                font=("Arial", 20, "bold"),
                width=4,
                pady=12
            ).grid(row=0, column=0, padx=16, pady=17)

            datos = tk.Frame(cabecera, bg=DOC_LATERAL)
            datos.grid(row=0, column=1, sticky="nsew", pady=17)

            tk.Label(
                datos,
                text=DIRECTOR["nombre"],
                bg=DOC_LATERAL,
                fg=DOC_BLANCO,
                font=("Arial", 15, "bold"),
                wraplength=350,
                justify="left"
            ).pack(anchor="w")

            tk.Label(
                datos,
                text=DIRECTOR["puesto"],
                bg=DOC_LATERAL,
                fg="#C5D5E8",
                font=("Arial", 9)
            ).pack(anchor="w", pady=(4, 6))

            tk.Label(
                datos,
                text="Número de empleado: " + DIRECTOR["numero"],
                bg=DOC_LATERAL,
                fg="#9DB9E0",
                font=("Arial", 9)
            ).pack(anchor="w")

            tk.Label(
                cabecera,
                text="● " + DIRECTOR["estado"],
                bg=DOC_VERDE_CLARO,
                fg=DOC_VERDE,
                font=("Arial", 8, "bold"),
                padx=8,
                pady=6
            ).grid(row=0, column=2, padx=13, pady=14, sticky="ne")

            informacion = crear_seccion(
                contenido,
                "Información del director",
                "Datos generales del responsable de la dirección escolar."
            )

            crear_dato(
                informacion, "Nombre completo",
                DIRECTOR["nombre"], 0, 0
            )
            crear_dato(
                informacion, "Cargo",
                DIRECTOR["puesto"], 0, 1
            )
            crear_dato(
                informacion, "Número de empleado",
                DIRECTOR["numero"], 1, 0
            )
            crear_dato(
                informacion, "Fecha de ingreso",
                DIRECTOR["ingreso"], 1, 1
            )

            contacto = crear_seccion(
                contenido,
                "Contacto",
                "Información para la comunicación con la dirección del plantel."
            )

            crear_dato(
                contacto, "Correo electrónico",
                DIRECTOR["correo"], 0, 0
            )
            crear_dato(
                contacto, "Teléfono",
                DIRECTOR["telefono"], 0, 1
            )

            plantel = crear_seccion(
                contenido,
                "Información del plantel",
                "Datos del centro educativo en el que desempeña sus funciones."
            )

            crear_dato(
                plantel, "Nombre del plantel",
                DIRECTOR["plantel"], 0, 0
            )
            crear_dato(
                plantel, "Área",
                DIRECTOR["area"], 0, 1
            )

            tk.Label(
                contenido,
                text="CONTROL ESCOLAR  •  Perfil del director",
                bg=DOC_FONDO,
                fg=DOC_GRIS,
                font=("Arial", 8)
            ).pack(anchor="w", padx=22, pady=(0, 15))


        def pantalla_grupos():
            limpiar_body("Administrar grupos")
            lienzo, cont = crear_area_desplazable(body, DOC_FONDO)

            tk.Label(
                cont, text="GESTIÓN ESCOLAR  /  ORGANIZACIÓN",
                bg=DOC_FONDO, fg=DOC_AZUL,
                font=("Arial", 8, "bold")
            ).pack(anchor="w", padx=22, pady=(19, 5))

            tk.Label(
                cont, text="Administrar grupos",
                bg=DOC_FONDO, fg=DOC_TEXTO,
                font=("Arial", 21, "bold")
            ).pack(anchor="w", padx=22)

            tk.Label(
                cont,
                text="Crea grupos escolares y administra la lista de alumnos.",
                bg=DOC_FONDO, fg=DOC_GRIS, font=("Arial", 10),
                wraplength=650, justify="left"
            ).pack(anchor="w", padx=22, pady=(4, 15))

            principal = tk.Frame(cont, bg=DOC_FONDO)
            principal.pack(fill="both", expand=True, padx=18, pady=(0, 15))
            principal.grid_columnconfigure(0, weight=1, minsize=190)
            principal.grid_columnconfigure(1, weight=2, minsize=260)

            panel_grupos = tk.Frame(
                principal, bg=DOC_BLANCO,
                highlightbackground=DOC_BORDE, highlightthickness=1
            )
            panel_grupos.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

            tk.Label(
                panel_grupos, text="Grupos registrados",
                bg=DOC_BLANCO, fg=DOC_TEXTO,
                font=("Arial", 12, "bold")
            ).pack(anchor="w", padx=14, pady=(15, 4))

            tk.Label(
                panel_grupos,
                text="Selecciona un grupo para ver sus alumnos.",
                bg=DOC_BLANCO, fg=DOC_GRIS, font=("Arial", 9),
                wraplength=210, justify="left"
            ).pack(anchor="w", padx=14, pady=(0, 10))

            marco_lista = tk.Frame(panel_grupos, bg=DOC_BLANCO)
            marco_lista.pack(fill="both", expand=True, padx=12, pady=(0, 12))

            lista_grupos = tk.Listbox(
                marco_lista, font=("Arial", 10), bg="#F8FAFC",
                fg=DOC_TEXTO, selectbackground=DOC_AZUL,
                selectforeground=DOC_BLANCO, relief="flat",
                highlightthickness=1, highlightbackground=DOC_BORDE,
                activestyle="none", height=9, exportselection=False
            )
            barra_lista = ttk.Scrollbar(
                marco_lista, orient="vertical", command=lista_grupos.yview
            )
            lista_grupos.configure(yscrollcommand=barra_lista.set)
            lista_grupos.pack(side="left", fill="both", expand=True)
            barra_lista.pack(side="right", fill="y")

            tk.Label(
                panel_grupos, text="Nombre del grupo",
                bg=DOC_BLANCO, fg=DOC_GRIS, font=("Arial", 8, "bold")
            ).pack(anchor="w", padx=12, pady=(2, 4))

            entrada_grupo = tk.Entry(
                panel_grupos, font=("Arial", 10), bg="#F8FAFC",
                fg=DOC_TEXTO, relief="flat", highlightthickness=1,
                highlightbackground=DOC_BORDE, highlightcolor=DOC_AZUL
            )
            entrada_grupo.pack(fill="x", padx=12, pady=(0, 10), ipady=7)

            panel_alumnos = tk.Frame(
                principal, bg=DOC_BLANCO,
                highlightbackground=DOC_BORDE, highlightthickness=1
            )
            panel_alumnos.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

            tk.Label(
                panel_alumnos, text="Alumnos del grupo",
                bg=DOC_BLANCO, fg=DOC_TEXTO,
                font=("Arial", 12, "bold")
            ).pack(anchor="w", padx=15, pady=(15, 4))

            etiqueta_grupo = tk.Label(
                panel_alumnos, text="Selecciona un grupo",
                bg=DOC_AZUL_CLARO, fg=DOC_AZUL_OSCURO,
                font=("Arial", 9, "bold"), padx=10, pady=7
            )
            etiqueta_grupo.pack(anchor="w", padx=15, pady=(4, 10))

            marco_tabla = tk.Frame(panel_alumnos, bg=DOC_BLANCO)
            marco_tabla.pack(fill="both", expand=True, padx=12)

            tabla_alumnos = ttk.Treeview(
                marco_tabla, columns=("numero", "nombre"),
                show="headings", height=9, selectmode="browse"
            )
            tabla_alumnos.heading("numero", text="N.º")
            tabla_alumnos.heading("nombre", text="Nombre del alumno")
            tabla_alumnos.column(
                "numero", width=45, minwidth=40,
                anchor="center", stretch=False
            )
            tabla_alumnos.column(
                "nombre", width=230, minwidth=120,
                anchor="w", stretch=True
            )

            barra_tabla = ttk.Scrollbar(
                marco_tabla, orient="vertical", command=tabla_alumnos.yview
            )
            tabla_alumnos.configure(yscrollcommand=barra_tabla.set)
            tabla_alumnos.pack(side="left", fill="both", expand=True)
            barra_tabla.pack(side="right", fill="y")

            etiqueta_total = tk.Label(
                panel_alumnos, text="Total de alumnos: 0",
                bg=DOC_BLANCO, fg=DOC_GRIS, font=("Arial", 9, "bold")
            )
            etiqueta_total.pack(anchor="w", padx=15, pady=10)

            tk.Frame(panel_alumnos, bg=DOC_BORDE, height=1).pack(
                fill="x", padx=12
            )

            tk.Label(
                panel_alumnos, text="Nombre del alumno",
                bg=DOC_BLANCO, fg=DOC_GRIS, font=("Arial", 8, "bold")
            ).pack(anchor="w", padx=15, pady=(12, 4))

            entrada_alumno = tk.Entry(
                panel_alumnos, font=("Arial", 10), bg="#F8FAFC",
                fg=DOC_TEXTO, relief="flat", highlightthickness=1,
                highlightbackground=DOC_BORDE, highlightcolor=DOC_AZUL
            )
            entrada_alumno.pack(fill="x", padx=15, pady=(0, 12), ipady=8)

            def grupo_seleccionado():
                seleccion = lista_grupos.curselection()
                return lista_grupos.get(seleccion[0]) if seleccion else None

            def actualizar_tabla():
                grupo = grupo_seleccionado()

                for elemento in tabla_alumnos.get_children():
                    tabla_alumnos.delete(elemento)

                if grupo is None or grupo not in GRUPOS_ALUMNOS:
                    etiqueta_grupo.config(text="Selecciona un grupo")
                    etiqueta_total.config(text="Total de alumnos: 0")
                    return

                etiqueta_grupo.config(text="Grupo: " + grupo)

                for numero, nombre in enumerate(GRUPOS_ALUMNOS[grupo], start=1):
                    tabla_alumnos.insert("", "end", values=(numero, nombre))

                etiqueta_total.config(
                    text=f"Total de alumnos: {len(GRUPOS_ALUMNOS[grupo])}"
                )

            def actualizar_lista(seleccionar=None):
                lista_grupos.delete(0, "end")
                nombres = sorted(GRUPOS_ALUMNOS.keys())

                for nombre in nombres:
                    lista_grupos.insert("end", nombre)

                if seleccionar in nombres:
                    indice = nombres.index(seleccionar)
                elif nombres:
                    indice = 0
                else:
                    actualizar_tabla()
                    return

                lista_grupos.selection_set(indice)
                lista_grupos.activate(indice)
                lista_grupos.see(indice)
                actualizar_tabla()

            def seleccionar_grupo(event=None):
                actualizar_tabla()
                entrada_alumno.delete(0, "end")

            lista_grupos.bind("<<ListboxSelect>>", seleccionar_grupo)

            def crear_grupo():
                nombre = entrada_grupo.get().strip().upper()

                if not nombre:
                    messagebox.showwarning("Dato faltante", "Escribe el nombre del grupo.")
                    return

                if nombre in GRUPOS_ALUMNOS:
                    messagebox.showwarning("Grupo existente", "Ya existe un grupo con ese nombre.")
                    return

                GRUPOS_ALUMNOS[nombre] = []
                entrada_grupo.delete(0, "end")
                actualizar_lista(nombre)
                messagebox.showinfo("Grupo creado", f"El grupo {nombre} se creó correctamente.")

            def eliminar_grupo():
                nombre = grupo_seleccionado()

                if nombre is None:
                    messagebox.showwarning("Sin selección", "Selecciona el grupo que deseas eliminar.")
                    return

                confirmar = messagebox.askyesno(
                    "Eliminar grupo",
                    f"¿Deseas eliminar el grupo {nombre}?\n\n"
                    "También se eliminará su lista de alumnos de esta demostración."
                )

                if confirmar:
                    del GRUPOS_ALUMNOS[nombre]
                    entrada_alumno.delete(0, "end")
                    actualizar_lista()

            def agregar_alumno():
                grupo = grupo_seleccionado()
                nombre = entrada_alumno.get().strip()

                if grupo is None:
                    messagebox.showwarning("Sin selección", "Primero selecciona un grupo.")
                    return

                if not nombre:
                    messagebox.showwarning("Dato faltante", "Escribe el nombre del alumno.")
                    return

                if any(alumno.lower() == nombre.lower() for alumno in GRUPOS_ALUMNOS[grupo]):
                    messagebox.showwarning("Alumno existente", "Ese alumno ya está registrado en este grupo.")
                    return

                GRUPOS_ALUMNOS[grupo].append(nombre)
                entrada_alumno.delete(0, "end")
                actualizar_tabla()

            def editar_alumno():
                grupo = grupo_seleccionado()
                seleccion = tabla_alumnos.selection()
                nuevo_nombre = entrada_alumno.get().strip()

                if grupo is None:
                    messagebox.showwarning("Sin selección", "Selecciona un grupo.")
                    return

                if not seleccion:
                    messagebox.showwarning("Sin selección", "Selecciona al alumno que deseas editar.")
                    return

                if not nuevo_nombre:
                    messagebox.showwarning("Dato faltante", "Escribe el nuevo nombre del alumno.")
                    return

                valores = tabla_alumnos.item(seleccion[0], "values")
                indice = int(valores[0]) - 1

                if any(
                    i != indice and alumno.lower() == nuevo_nombre.lower()
                    for i, alumno in enumerate(GRUPOS_ALUMNOS[grupo])
                ):
                    messagebox.showwarning("Alumno existente", "Ya existe otro alumno con ese nombre en el grupo.")
                    return

                GRUPOS_ALUMNOS[grupo][indice] = nuevo_nombre
                entrada_alumno.delete(0, "end")
                actualizar_tabla()

            def eliminar_alumno():
                grupo = grupo_seleccionado()
                seleccion = tabla_alumnos.selection()

                if grupo is None:
                    messagebox.showwarning("Sin selección", "Selecciona un grupo.")
                    return

                if not seleccion:
                    messagebox.showwarning("Sin selección", "Selecciona al alumno que deseas eliminar.")
                    return

                valores = tabla_alumnos.item(seleccion[0], "values")
                indice = int(valores[0]) - 1
                nombre = GRUPOS_ALUMNOS[grupo][indice]

                if messagebox.askyesno(
                    "Eliminar alumno",
                    f"¿Deseas eliminar a {nombre} del grupo {grupo}?"
                ):
                    GRUPOS_ALUMNOS[grupo].pop(indice)
                    entrada_alumno.delete(0, "end")
                    actualizar_tabla()

            def cargar_nombre_alumno(event=None):
                seleccion = tabla_alumnos.selection()
                if not seleccion:
                    return
                valores = tabla_alumnos.item(seleccion[0], "values")
                entrada_alumno.delete(0, "end")
                entrada_alumno.insert(0, valores[1])

            tabla_alumnos.bind("<<TreeviewSelect>>", cargar_nombre_alumno)

            botones_grupos = tk.Frame(panel_grupos, bg=DOC_BLANCO)
            botones_grupos.pack(fill="x", padx=12, pady=(0, 14))

            tk.Button(
                botones_grupos, text="Crear grupo", command=crear_grupo,
                bg=DOC_AZUL, fg=DOC_BLANCO,
                activebackground=DOC_AZUL_OSCURO,
                activeforeground=DOC_BLANCO,
                font=("Arial", 9, "bold"), relief="flat",
                cursor="hand2", bd=0, pady=9
            ).pack(fill="x", pady=(0, 7))

            tk.Button(
                botones_grupos, text="Eliminar grupo", command=eliminar_grupo,
                bg="#FDE8E7", fg="#B42318",
                activebackground="#F9D2D0", activeforeground="#B42318",
                font=("Arial", 9, "bold"), relief="flat",
                cursor="hand2", bd=0, pady=9
            ).pack(fill="x")

            botones_alumnos = tk.Frame(panel_alumnos, bg=DOC_BLANCO)
            botones_alumnos.pack(fill="x", padx=15, pady=(0, 15))

            tk.Button(
                botones_alumnos, text="Agregar alumno", command=agregar_alumno,
                bg=DOC_AZUL, fg=DOC_BLANCO,
                activebackground=DOC_AZUL_OSCURO,
                activeforeground=DOC_BLANCO,
                font=("Arial", 9, "bold"), relief="flat",
                cursor="hand2", bd=0, padx=10, pady=9
            ).pack(side="left", fill="x", expand=True, padx=(0, 4))

            tk.Button(
                botones_alumnos, text="Editar", command=editar_alumno,
                bg=DOC_VERDE_CLARO, fg=DOC_VERDE,
                activebackground="#C8F0DF", activeforeground=DOC_VERDE,
                font=("Arial", 9, "bold"), relief="flat",
                cursor="hand2", bd=0, padx=10, pady=9
            ).pack(side="left", fill="x", expand=True, padx=4)

            tk.Button(
                botones_alumnos, text="Eliminar", command=eliminar_alumno,
                bg="#FDE8E7", fg="#B42318",
                activebackground="#F9D2D0", activeforeground="#B42318",
                font=("Arial", 9, "bold"), relief="flat",
                cursor="hand2", bd=0, padx=10, pady=9
            ).pack(side="left", fill="x", expand=True, padx=(4, 0))

            actualizar_lista()

        # HISTORIAL

        def pantalla_historial():
            movimientos = [
                ("27/10/2026", "Asistencia", "Asistencia de 3° A actualizada", "3° A", "Laura Sánchez Pérez"),
                ("27/10/2026", "Justificante", "Justificante de Ana López Martínez", "1° A", "Ana Torres López"),
                ("26/10/2026", "Incidencia", "Incidencia de conducta · Mateo Flores Díaz", "2° A", "Carlos Méndez Ruiz"),
                ("26/10/2026", "Carta compromiso", "Carta compromiso · Diego Ramírez Flores", "4° A", "Dirección"),
                ("24/10/2026", "Asistencia", "Asistencia de 5° A registrada", "5° A", "María Flores Díaz"),
                ("23/10/2026", "Incidencia", "Incidencia académica · Daniela Ruiz López", "5° A", "María Flores Díaz"),
                ("23/10/2026", "Justificante", "Justificante de Camila Torres Reyes", "3° A", "Laura Sánchez Pérez"),
                ("22/10/2026", "Carta compromiso", "Carta compromiso · Sebastián Morales Vega", "5° A", "Dirección"),
                ("21/10/2026", "Asistencia", "Asistencia de 6° A registrada", "6° A", "Roberto Cruz Vega"),
                ("20/10/2026", "Incidencia", "Incidente · Emiliano Cruz Morales", "3° A", "Laura Sánchez Pérez")
            ]

            colores_tipo = {
                "Asistencia": (DOC_AZUL_CLARO, DOC_AZUL_OSCURO),
                "Justificante": (DOC_VERDE_CLARO, DOC_VERDE),
                "Incidencia": ("#FDE8E7", "#B42318"),
                "Carta compromiso": ("#FFF3DF", "#C9822B")
            }

            limpiar_body(f"Historial - {len(movimientos)} movimientos")
            lienzo, contenido = crear_area_desplazable(body, DOC_FONDO)

            tk.Label(
                contenido, text="GESTIÓN ESCOLAR  /  REGISTRO",
                bg=DOC_FONDO, fg=DOC_AZUL,
                font=("Arial", 8, "bold")
            ).pack(anchor="w", padx=22, pady=(19, 5))

            tk.Label(
                contenido, text="Historial",
                bg=DOC_FONDO, fg=DOC_TEXTO,
                font=("Arial", 21, "bold")
            ).pack(anchor="w", padx=22)

            tk.Label(
                contenido,
                text="Consulta los movimientos recientes registrados en el plantel.",
                bg=DOC_FONDO, fg=DOC_GRIS, font=("Arial", 10),
                wraplength=650, justify="left"
            ).pack(anchor="w", padx=22, pady=(4, 15))

            banner = tk.Frame(contenido, bg=DOC_LATERAL)
            banner.pack(fill="x", padx=18, pady=(0, 15))
            banner.grid_columnconfigure(0, weight=1)

            texto_banner = tk.Frame(banner, bg=DOC_LATERAL)
            texto_banner.grid(row=0, column=0, sticky="w", padx=18, pady=17)

            tk.Label(
                texto_banner, text="REGISTRO DE ACTIVIDAD",
                bg=DOC_LATERAL, fg="#9DB9E0",
                font=("Arial", 8, "bold")
            ).pack(anchor="w")

            tk.Label(
                texto_banner, text="Movimientos del plantel",
                bg=DOC_LATERAL, fg=DOC_BLANCO,
                font=("Arial", 17, "bold")
            ).pack(anchor="w", pady=(4, 3))

            tk.Label(
                texto_banner,
                text="Asistencias, justificantes, incidencias y cartas.",
                bg=DOC_LATERAL, fg="#D0DCEC", font=("Arial", 9),
                wraplength=320, justify="left"
            ).pack(anchor="w")

            contador = tk.Frame(
                banner, bg=DOC_LATERAL_CLARO,
                highlightbackground="#3B5778", highlightthickness=1
            )
            contador.grid(row=0, column=1, padx=16, pady=14)

            tk.Label(
                contador, text=str(len(movimientos)),
                bg=DOC_LATERAL_CLARO, fg=DOC_BLANCO,
                font=("Arial", 23, "bold")
            ).pack(padx=20, pady=(10, 0))

            tk.Label(
                contador, text="MOVIMIENTOS",
                bg=DOC_LATERAL_CLARO, fg="#C5D5E8",
                font=("Arial", 8, "bold")
            ).pack(padx=12, pady=(0, 10))

            filtros = tk.Frame(
                contenido, bg=DOC_BLANCO,
                highlightbackground=DOC_BORDE, highlightthickness=1
            )
            filtros.pack(fill="x", padx=18, pady=(0, 15))

            interior = tk.Frame(filtros, bg=DOC_BLANCO)
            interior.pack(fill="x", padx=14, pady=14)
            for columna in range(4):
                interior.grid_columnconfigure(columna, weight=1, uniform="filtro")

            def pad_filtro(columna):
                return (0 if columna == 0 else 8, 0 if columna == 3 else 8)

            def etiqueta_filtro(texto, columna):
                tk.Label(
                    interior, text=texto.upper(), bg=DOC_BLANCO,
                    fg=DOC_GRIS, font=("Arial", 8, "bold"), padx=0
                ).grid(
                    row=0, column=columna, sticky="w",
                    padx=pad_filtro(columna), pady=(0, 5)
                )

            etiqueta_filtro("Buscar", 0)
            tk.Entry(
                interior, font=("Arial", 10), bg="#F8FAFC", fg=DOC_TEXTO,
                relief="flat", highlightthickness=1,
                highlightbackground=DOC_BORDE, highlightcolor=DOC_AZUL,
                insertbackground=DOC_TEXTO
            ).grid(row=1, column=0, sticky="ew", padx=pad_filtro(0), ipady=8)

            etiqueta_filtro("Tipo de movimiento", 1)
            combo_tipo = ttk.Combobox(
                interior, state="readonly", font=("Arial", 10),
                values=["Todos", "Asistencia", "Justificante",
                        "Incidencia", "Carta compromiso"]
            )
            combo_tipo.grid(row=1, column=1, sticky="ew", padx=pad_filtro(1), ipady=5)
            combo_tipo.set("Todos")

            etiqueta_filtro("Desde", 2)
            SelectorFecha(
                interior, inicial=date.today().replace(day=1),
                fuente=("Arial", 10), fondo="#F8FAFC", borde=DOC_BORDE,
                acento=DOC_AZUL, acento_claro=DOC_AZUL_CLARO,
                texto=DOC_TEXTO, suave=DOC_GRIS, ipady=8
            ).grid(row=1, column=2, sticky="ew", padx=pad_filtro(2))

            etiqueta_filtro("Hasta", 3)
            SelectorFecha(
                interior, fuente=("Arial", 10), fondo="#F8FAFC",
                borde=DOC_BORDE, acento=DOC_AZUL,
                acento_claro=DOC_AZUL_CLARO, texto=DOC_TEXTO,
                suave=DOC_GRIS, ipady=8
            ).grid(row=1, column=3, sticky="ew", padx=pad_filtro(3))

            botones_filtro = tk.Frame(interior, bg=DOC_BLANCO)
            botones_filtro.grid(row=2, column=0, columnspan=4, sticky="e", pady=(14, 0))

            tk.Button(
                botones_filtro, text="Exportar", bg=DOC_AZUL_CLARO,
                fg=DOC_AZUL_OSCURO, activebackground=DOC_AZUL_CLARO,
                activeforeground=DOC_AZUL_OSCURO, font=("Arial", 9, "bold"),
                relief="flat", bd=0, cursor="hand2", padx=16, pady=8
            ).pack(side="left", padx=(0, 8))

            tk.Button(
                botones_filtro, text="Filtrar", bg=DOC_AZUL, fg=DOC_BLANCO,
                activebackground=DOC_AZUL_OSCURO, activeforeground=DOC_BLANCO,
                font=("Arial", 9, "bold"), relief="flat", bd=0,
                cursor="hand2", padx=16, pady=8
            ).pack(side="left")

            zona_lista = tk.Frame(contenido, bg=DOC_FONDO)
            zona_lista.pack(fill="x", padx=18, pady=(0, 6))

            tk.Label(
                zona_lista, text="Actividad reciente",
                bg=DOC_FONDO, fg=DOC_TEXTO,
                font=("Arial", 12, "bold")
            ).pack(side="left")

            tk.Label(
                zona_lista, text="ÚLTIMOS 30 DÍAS",
                bg=DOC_AZUL_CLARO, fg=DOC_AZUL_OSCURO,
                font=("Arial", 8, "bold"), padx=8, pady=4
            ).pack(side="right")

            tabla = tk.Frame(contenido, bg=DOC_FONDO)
            tabla.pack(fill="x", padx=18, pady=(0, 10))

            def configurar_columnas(fila):
                fila.grid_columnconfigure(0, weight=0, minsize=95)
                fila.grid_columnconfigure(1, weight=0, minsize=135)
                fila.grid_columnconfigure(2, weight=5, minsize=160)
                fila.grid_columnconfigure(3, weight=0, minsize=60)
                fila.grid_columnconfigure(4, weight=2, minsize=110)

            cabecera = tk.Frame(tabla, bg="#E5ECF6")
            cabecera.pack(fill="x", pady=(0, 4))
            configurar_columnas(cabecera)

            for columna, texto in enumerate(
                ["FECHA", "TIPO", "DETALLE", "GRUPO", "REGISTRÓ"]
            ):
                tk.Label(
                    cabecera, text=texto, bg="#E5ECF6", fg=DOC_GRIS,
                    font=("Arial", 8, "bold"),
                    anchor="w" if columna in (0, 2, 4) else "center",
                    padx=10, pady=10
                ).grid(row=0, column=columna, sticky="nsew")

            for fecha, tipo, detalle, grupo, quien in movimientos:
                fila = tk.Frame(
                    tabla, bg=DOC_BLANCO,
                    highlightbackground=DOC_BORDE, highlightthickness=1
                )
                fila.pack(fill="x", pady=2)
                configurar_columnas(fila)

                tk.Label(
                    fila, text=fecha, bg=DOC_BLANCO, fg=DOC_GRIS,
                    font=("Arial", 9), anchor="w", padx=10
                ).grid(row=0, column=0, sticky="nsew", pady=12)

                fondo_chip, texto_chip = colores_tipo[tipo]
                tk.Label(
                    fila, text=tipo, bg=fondo_chip, fg=texto_chip,
                    font=("Arial", 8, "bold"), padx=8, pady=4
                ).grid(row=0, column=1, padx=6, pady=10)

                tk.Label(
                    fila, text=detalle, bg=DOC_BLANCO, fg=DOC_TEXTO,
                    font=("Arial", 9, "bold"), anchor="w", padx=10,
                    wraplength=330, justify="left"
                ).grid(row=0, column=2, sticky="nsew", pady=10)

                tk.Label(
                    fila, text=grupo, bg=DOC_AZUL_CLARO, fg=DOC_AZUL_OSCURO,
                    font=("Arial", 8, "bold"), padx=5, pady=4
                ).grid(row=0, column=3, padx=3, pady=10)

                tk.Label(
                    fila, text=quien, bg=DOC_BLANCO, fg=DOC_GRIS,
                    font=("Arial", 8), anchor="w", padx=10,
                    wraplength=150, justify="left"
                ).grid(row=0, column=4, sticky="nsew", pady=10)

            tk.Label(
                contenido,
                text=f"Mostrando {len(movimientos)} de {len(movimientos)} movimientos  •  Datos de demostración",
                bg=DOC_FONDO, fg=DOC_GRIS, font=("Arial", 8)
            ).pack(anchor="w", padx=22, pady=(0, 15))


        tk.Label(
            sidebar, text="Plantel Educativo",
            font=("Arial", 11, "bold"), bg=LATERAL,
            fg=BLANCO, anchor="w"
        ).pack(pady=(20, 2), padx=15, anchor="w")

        tk.Label(
            sidebar, text="Gestión Escolar",
            font=("Arial", 8), bg=LATERAL,
            fg="#8CA3C7", anchor="w"
        ).pack(padx=15, anchor="w", pady=(0, 20))

        opciones = [
            ("Inicio", pantalla_inicio),
            ("Docentes", pantalla_docentes),
            ("Cartas compromiso", pantalla_cartas),
            ("Administrar grupos", pantalla_grupos),
            ("Historial", pantalla_historial),
            ("Mi perfil", pantalla_perfil)
        ]

        for nombre, funcion in opciones:
            tk.Button(
                sidebar, text=nombre, bg=LATERAL, fg="#9BB0C8",
                font=("Arial", 9), relief="flat", bd=0,
                anchor="w", padx=15, pady=12, cursor="hand2",
                activebackground=SEL, activeforeground=BLANCO,
                command=funcion
            ).pack(fill="x", padx=8, pady=1)

        tk.Button(
            sidebar,
            text="Cerrar sesión",
            command=cerrar_panel_director,
            bg="#D94F54",
            fg=BLANCO,
            activebackground="#B9383E",
            activeforeground=BLANCO,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            pady=11
        ).pack(side="bottom", fill="x", padx=12, pady=18)

        pantalla_inicio()

    def cerrar_panel_director():
        if messagebox.askyesno("Cerrar sesión", "¿Deseas volver al inicio de sesión?"):
            root.unbind_all("<MouseWheel>")
            root.unbind_all("<Button-4>")
            root.unbind_all("<Button-5>")
            root.destroy()
            ventana.deiconify()
            ventana.state("zoomed")
            entrada_usuario.delete(0, tk.END)
            entrada_contrasena.delete(0, tk.END)
            entrada_codigo.delete(0, tk.END)
            var_codigo.set(False)
            mostrar_codigo()
            entrada_usuario.focus_set()

    crear_app()
    root.protocol("WM_DELETE_WINDOW", cerrar_panel_director)


def abrir_panel_maestro(panel, usuario):
    panel.title("Sistema de Gestión Escolar - Panel docente")
    panel.minsize(620, 430)
    try:
        panel.state("zoomed")
    except tk.TclError:
        panel.geometry("1100x700")

    FONDO = "#F3F6FA"
    BLANCO = "#FFFFFF"
    MARINO = "#172B4D"
    MARINO_CLARO = "#243F66"
    AZUL = "#356AE6"
    AZUL_HOVER = "#2857C5"
    AZUL_SUAVE = "#EAF0FF"
    VERDE = "#168568"
    VERDE_SUAVE = "#E5F5EF"
    ROJO = "#D94F54"
    ROJO_SUAVE = "#FCEBEC"
    NARANJA = "#C9822B"
    NARANJA_SUAVE = "#FFF3DF"
    TEXTO = "#24344D"
    SECUNDARIO = "#718096"
    BORDE = "#E2E8F0"
    CAMPO = "#F8FAFC"

    NOMBRE_MAESTRO = usuario if usuario else "Juan Pérez García"
    GRUPO_MAESTRO = "3° A"
    PLANTEL = "Primaria Nezahualcóyotl"

    ALUMNOS = [
        "Ana López Martínez",
        "Carlos Hernández Ruiz",
        "Sofía García Torres",
        "Diego Ramírez Flores",
        "Valeria Sánchez Cruz",
        "Mateo Flores Díaz",
        "Camila Torres Reyes",
        "Emiliano Cruz Morales",
        "Daniela Ruiz López",
        "Sebastián Morales Vega"
    ]

    asistencias = {}
    justificantes = []
    incidencias = []
    area_contenido = None
    lienzo_contenido = None
    botones_menu = {}

    def configurar_estilos():
        estilo = ttk.Style()
        estilo.theme_use("clam")

        estilo.configure(
            "Tabla.Treeview",
            background=BLANCO,
            foreground=TEXTO,
            fieldbackground=BLANCO,
            rowheight=38,
            borderwidth=0,
            font=("Segoe UI", 10)
        )

        estilo.configure(
            "Tabla.Treeview.Heading",
            background="#EDF2F8",
            foreground=MARINO,
            font=("Segoe UI", 10, "bold"),
            padding=(12, 12),
            relief="flat"
        )

        estilo.map(
            "Tabla.Treeview",
            background=[("selected", AZUL_SUAVE)],
            foreground=[("selected", MARINO)]
        )

        estilo.configure(
            "Campo.TCombobox",
            padding=9,
            font=("Segoe UI", 10)
        )

        estilo.map(
            "Campo.TCombobox",
            fieldbackground=[("readonly", CAMPO)],
            selectbackground=[("readonly", CAMPO)],
            selectforeground=[("readonly", TEXTO)]
        )

    root = panel
    root.title("Sistema de Gestión Escolar")
    root.geometry("1250x780")
    root.minsize(1000, 650)
    root.configure(bg=FONDO)
    root.state("zoomed")

    configurar_estilos()

    def limpiar_contenido():
        for widget in area_contenido.winfo_children():
            widget.destroy()

    def boton_padre(parent, texto, comando, color=AZUL, ancho=None):
        boton = tk.Button(
            parent,
            text=texto,
            command=comando,
            bg=AZUL,
            fg=BLANCO,
            activebackground=AZUL_HOVER,
            activeforeground=BLANCO,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18,
            pady=11
        )

        if ancho:
            boton.config(width=ancho)

        return boton

    def tarjeta(parent, padding=20):
        return tk.Frame(
            parent,
            bg=BLANCO,
            padx=padding,
            pady=padding,
            highlightbackground=BORDE,
            highlightthickness=1
        )

    def etiqueta(parent, texto, tamano=10, color=TEXTO, negrita=False):
        return tk.Label(
            parent,
            text=texto,
            bg=parent.cget("bg"),
            fg=color,
            font=("Segoe UI", tamano, "bold" if negrita else "normal"),
            anchor="w"
        )

    def crear_entrada(parent, ancho=35):
        return tk.Entry(
            parent,
            width=ancho,
            font=("Segoe UI", 10),
            bg=CAMPO,
            fg=TEXTO,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDE,
            highlightcolor=AZUL,
            insertbackground=TEXTO
        )

    def crear_combo(parent, valores, ancho=28):
        return ttk.Combobox(
            parent,
            values=valores,
            width=ancho,
            state="readonly",
            style="Campo.TCombobox"
        )

    def encabezado(titulo, descripcion):
        limpiar_contenido()

        zona_titulo = tk.Frame(area_contenido, bg=FONDO)
        zona_titulo.pack(fill="x", pady=(0, 22))

        tk.Label(
            zona_titulo,
            text=titulo,
            bg=FONDO,
            fg=MARINO,
            font=("Segoe UI", 23, "bold"),
            anchor="w"
        ).pack(fill="x")

        tk.Label(
            zona_titulo,
            text=descripcion,
            bg=FONDO,
            fg=SECUNDARIO,
            font=("Segoe UI", 10),
            anchor="w"
        ).pack(fill="x", pady=(5, 0))

    def separador(parent):
        tk.Frame(parent, bg=BORDE, height=1).pack(fill="x", pady=15)

    def actualizar_menu(seleccionado):
        for nombre, boton in botones_menu.items():
            if nombre == seleccionado:
                boton.config(
                    bg=MARINO_CLARO,
                    fg=BLANCO,
                    font=("Segoe UI", 10, "bold")
                )
            else:
                boton.config(
                    bg=MARINO,
                    fg="#C8D3E2",
                    font=("Segoe UI", 10)
                )

    def abrir_pantalla(nombre, funcion):
        actualizar_menu(nombre)
        if lienzo_contenido is not None:
            lienzo_contenido.yview_moveto(0)
        funcion()

    def contar_asistencias(fecha):
        """Devuelve (asistieron, retardos, faltas, pendientes) de la fecha."""
        estados = [
            asistencias.get((fecha, alumno), ("", ""))[1]
            for alumno in ALUMNOS
        ]
        presentes = estados.count("Asistió")
        retardos = estados.count("Retardo")
        faltas = estados.count("Faltó")
        pendientes = len(ALUMNOS) - presentes - retardos - faltas
        return presentes, retardos, faltas, pendientes

    def crear_indicador(parent, titulo, valor, color, detalle):
        cuadro = tk.Frame(
            parent,
            bg=BLANCO,
            highlightbackground=BORDE,
            highlightthickness=1,
            padx=17,
            pady=17
        )
        cuadro.pack(side="left", fill="both", expand=True, padx=(0, 12))

        tk.Frame(cuadro, bg=color, height=4).pack(fill="x", pady=(0, 15))

        tk.Label(
            cuadro, text=titulo.upper(), bg=BLANCO,
            fg=SECUNDARIO, font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        tk.Label(
            cuadro, text=str(valor), bg=BLANCO,
            fg=MARINO, font=("Segoe UI", 25, "bold")
        ).pack(anchor="w", pady=(6, 2))

        tk.Label(
            cuadro, text=detalle, bg=BLANCO,
            fg=SECUNDARIO, font=("Segoe UI", 9)
        ).pack(anchor="w")

        return cuadro

    def pantalla_inicio():
        encabezado(
            "Panel principal",
            "Resumen de actividades y acceso a las funciones escolares."
        )

        fecha_hoy = date.today().strftime("%d/%m/%Y")
        presentes, retardos, faltas, pendientes = contar_asistencias(fecha_hoy)

        bienvenida = tk.Frame(
            area_contenido,
            bg=MARINO,
            padx=25,
            pady=23
        )
        bienvenida.pack(fill="x", pady=(0, 20))

        tk.Label(
            bienvenida,
            text="SISTEMA DE GESTIÓN ESCOLAR",
            bg=MARINO,
            fg="#AFC7FF",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        tk.Label(
            bienvenida,
            text=f"Bienvenido, {NOMBRE_MAESTRO}",
            bg=MARINO,
            fg=BLANCO,
            font=("Segoe UI", 19, "bold")
        ).pack(anchor="w", pady=(7, 4))

        tk.Label(
            bienvenida,
            text=f"{PLANTEL}  |  Grupo {GRUPO_MAESTRO}  |  {fecha_hoy}",
            bg=MARINO,
            fg="#D2DCEC",
            font=("Segoe UI", 10)
        ).pack(anchor="w")

        indicadores = tk.Frame(area_contenido, bg=FONDO)
        indicadores.pack(fill="x", pady=(0, 20))

        crear_indicador(
            indicadores, "Alumnos", len(ALUMNOS), AZUL,
            "Alumnos del grupo"
        )

        crear_indicador(
            indicadores, "Asistieron", presentes, VERDE,
            "Registro de hoy"
        )

        crear_indicador(
            indicadores, "Faltaron", faltas, ROJO,
            "Registro de hoy"
        )
        crear_indicador(
            indicadores, "Llegaron tarde", retardos, AMARILLO,
            "Registro de hoy"
        )
        crear_indicador(
            indicadores, "Pendientes", pendientes, NARANJA,
            "Sin registrar hoy"
        )

        accesos = tarjeta(area_contenido, 22)
        accesos.pack(fill="x")

        tk.Label(
            accesos,
            text="Accesos rápidos",
            bg=BLANCO,
            fg=MARINO,
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

        tk.Label(
            accesos,
            text="Selecciona una función para continuar.",
            bg=BLANCO,
            fg=SECUNDARIO,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(4, 17))

        fila = tk.Frame(accesos, bg=BLANCO)
        fila.pack(fill="x")

        boton_padre(
            fila, "Registrar asistencia",
            lambda: abrir_pantalla("Asistencias", pantalla_asistencias)
        ).pack(side="left", padx=(0, 10))

        boton_padre(
            fila, "Generar justificante",
            lambda: abrir_pantalla("Justificantes", pantalla_justificantes)
        ).pack(side="left", padx=(0, 10))

        boton_padre(
            fila, "Crear incidencia",
            lambda: abrir_pantalla("Incidencias", pantalla_incidencias)
        ).pack(side="left")

    def pantalla_asistencias():
        encabezado(
            "Control de asistencias",
            f"Registra la asistencia diaria del grupo {GRUPO_MAESTRO}."
        )

        fecha_hoy = date.today().strftime("%d/%m/%Y")
        AMARILLO_TEXTO = "#7A5C00"

        superior = tarjeta(area_contenido, 16)
        superior.pack(fill="x", pady=(0, 16))

        tk.Label(
            superior, text=f"Grupo: {GRUPO_MAESTRO}", bg=BLANCO,
            fg=MARINO, font=("Segoe UI", 11, "bold")
        ).pack(side="left")

        tk.Label(
            superior, text=f"Fecha de registro: {fecha_hoy}", bg=BLANCO,
            fg=SECUNDARIO, font=("Segoe UI", 10)
        ).pack(side="right")

        panel_asist = tarjeta(area_contenido, 16)
        panel_asist.pack(fill="both", expand=True)

        tk.Label(
            panel_asist, text="Lista de alumnos", bg=BLANCO,
            fg=MARINO, font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

        tk.Label(
            panel_asist, text="Selecciona una opción para cada alumno.",
            bg=BLANCO, fg=SECUNDARIO, font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(4, 15))

        tabla_frame = tk.Frame(panel_asist, bg=BLANCO)
        tabla_frame.pack(fill="both", expand=True)

        tabla_frame.columnconfigure(0, weight=3)
        for col in (1, 2, 3):
            tabla_frame.columnconfigure(col, weight=1, uniform="estado")

        for columna, texto in enumerate(
            ["Nombre del alumno", "Asistió", "Retardo", "Faltó"]
        ):
            tk.Label(
                tabla_frame, text=texto, bg="#EDF2F8", fg=MARINO,
                font=("Segoe UI", 10, "bold"), pady=12, padx=10,
                anchor="w" if columna == 0 else "center"
            ).grid(row=0, column=columna, sticky="nsew", padx=2, pady=2)

        botones_alumnos = {}

        COLORES = {
            "Asistió": (VERDE, BLANCO, VERDE_SUAVE, VERDE),
            "Retardo": (AMARILLO, AMARILLO_TEXTO, AMARILLO_CLARO, AMARILLO_TEXTO),
            "Faltó":   (ROJO, BLANCO, ROJO_SUAVE, ROJO),
        }

        def actualizar_botones(alumno):
            estado = asistencias.get((fecha_hoy, alumno), ("", ""))[1]
            for nombre_estado, boton in zip(
                ("Asistió", "Retardo", "Faltó"), botones_alumnos[alumno]
            ):
                activo_bg, activo_fg, suave_bg, suave_fg = COLORES[nombre_estado]
                if estado == nombre_estado:
                    boton.config(bg=activo_bg, fg=activo_fg)
                else:
                    boton.config(bg=suave_bg, fg=suave_fg)

        def cambiar_estado(alumno, estado):
            asistencias[(fecha_hoy, alumno)] = (fecha_hoy, estado)
            actualizar_botones(alumno)
            actualizar_resumen()

        def crear_boton_estado(texto, estado, alumno, fila, columna):
            activo_bg, activo_fg, suave_bg, suave_fg = COLORES[estado]
            boton = tk.Button(
                tabla_frame, text=texto,
                command=lambda: cambiar_estado(alumno, estado),
                bg=suave_bg, fg=suave_fg,
                activebackground=activo_bg, activeforeground=activo_fg,
                font=("Segoe UI", 9, "bold"),
                relief="flat", bd=0, cursor="hand2",
                width=12, pady=8
            )
            boton.grid(row=fila, column=columna, sticky="ew", padx=5, pady=4)
            return boton

        for fila, alumno in enumerate(ALUMNOS, start=1):
            fondo_fila = BLANCO if fila % 2 else "#F8FAFC"

            tk.Label(
                tabla_frame, text=alumno, bg=fondo_fila, fg=TEXTO,
                font=("Segoe UI", 10), anchor="w", padx=10, pady=10
            ).grid(row=fila, column=0, sticky="nsew", padx=2, pady=2)

            botones_alumnos[alumno] = (
                crear_boton_estado("✓  Asistió", "Asistió", alumno, fila, 1),
                crear_boton_estado("◷  Retardo", "Retardo", alumno, fila, 2),
                crear_boton_estado("✕  Faltó", "Faltó", alumno, fila, 3),
            )
            actualizar_botones(alumno)

        resumen = tk.Frame(panel_asist, bg=BLANCO)
        resumen.pack(fill="x", pady=(16, 0))

        resumen_texto = tk.Label(
            resumen, text="", bg=BLANCO, fg=SECUNDARIO,
            font=("Segoe UI", 10)
        )
        resumen_texto.pack(side="left")

        def actualizar_resumen():
            presentes, retardos, faltas, pendientes = contar_asistencias(fecha_hoy)
            resumen_texto.config(
                text=f"Asistieron: {presentes}   |   "
                     f"Retardos: {retardos}   |   "
                     f"Faltaron: {faltas}   |   "
                     f"Pendientes: {pendientes}"
            )

        def mostrar_resumen():
            presentes, retardos, faltas, pendientes = contar_asistencias(fecha_hoy)
            messagebox.showinfo(
                "Resumen de asistencia",
                f"Plantel: {PLANTEL}\n"
                f"Grupo: {GRUPO_MAESTRO}\n"
                f"Fecha: {fecha_hoy}\n\n"
                f"Asistieron: {presentes}\n"
                f"Llegaron tarde: {retardos}\n"
                f"Faltaron: {faltas}\n"
                f"Sin registrar: {pendientes}"
            )

        boton_padre(resumen, "Ver resumen", mostrar_resumen).pack(side="right")

        actualizar_resumen()

    def pantalla_justificantes():
        encabezado(
            "Generar justificante",
            "Registra y organiza las justificaciones de inasistencia."
        )

        GAP = 12  
        FONDO_VACIO = "#F1F5FF"
        BORDE_VACIO = "#B9CBF5"

        panel_just = tarjeta(area_contenido, 24)
        panel_just.pack(fill="x")
        panel_just.columnconfigure(0, weight=1, uniform="col")
        panel_just.columnconfigure(1, weight=1, uniform="col")

        def pad(col):
            return (0, GAP) if col == 0 else (GAP, 0)

        def etiqueta_campo(texto, fila, col):
            tk.Label(
                panel_just, text=texto.upper(), bg=BLANCO, fg=SECUNDARIO,
                font=("Segoe UI", 8, "bold"), anchor="w", padx=0, bd=0
            ).grid(row=fila, column=col, sticky="w", padx=pad(col), pady=(0, 6))

        tk.Label(
            panel_just, text="Información del justificante", bg=BLANCO,
            fg=MARINO, font=("Segoe UI", 14, "bold"), anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        tk.Label(
            panel_just,
            text="Completa los datos de la ausencia y adjunta la evidencia.",
            bg=BLANCO, fg=SECUNDARIO, font=("Segoe UI", 9), anchor="w"
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 14))

        tk.Frame(panel_just, bg=BORDE, height=1).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(0, 18)
        )

        etiqueta_campo("Alumno", 3, 0)
        alumno_combo = BuscadorAlumno(
            panel_just, ALUMNOS, fuente=("Segoe UI", 10), fondo=CAMPO,
            borde=BORDE, acento=AZUL, acento_claro=AZUL_SUAVE,
            texto=TEXTO, suave=SECUNDARIO, ipady=8
        )
        alumno_combo.grid(row=4, column=0, sticky="ew", padx=pad(0), pady=(0, 18))

        etiqueta_campo("Grupo", 3, 1)
        grupo = crear_entrada(panel_just, 32)
        grupo.grid(row=4, column=1, sticky="ew", padx=pad(1), pady=(0, 18), ipady=8)
        grupo.insert(0, GRUPO_MAESTRO)
        grupo.config(
            state="readonly", readonlybackground="#EEF2F7", fg=SECUNDARIO
        )

        etiqueta_campo("Fecha de la ausencia", 5, 0)
        fecha_entry = SelectorFecha(
            panel_just, fuente=("Segoe UI", 10), fondo=CAMPO, borde=BORDE,
            acento=AZUL, acento_claro=AZUL_SUAVE, texto=TEXTO,
            suave=SECUNDARIO, ipady=8
        )
        fecha_entry.grid(row=6, column=0, sticky="ew", padx=pad(0), pady=(0, 18))

        etiqueta_campo("Tipo de justificante", 5, 1)
        tipo_var = tk.StringVar(value="Enfermedad")
        tipo_frame = tk.Frame(panel_just, bg=BLANCO)
        tipo_frame.grid(row=6, column=1, sticky="ew", padx=pad(1), pady=(0, 18))

        for i, tipo in enumerate(["Enfermedad", "Familiar", "Otro"]):
            tipo_frame.columnconfigure(i, weight=1, uniform="tipo")
            tk.Radiobutton(
                tipo_frame, text=tipo, variable=tipo_var, value=tipo,
                indicatoron=0, bg=CAMPO, fg=TEXTO,
                selectcolor=AZUL_SUAVE, activebackground=AZUL_SUAVE,
                activeforeground=AZUL, font=("Segoe UI", 10),
                relief="flat", bd=0, cursor="hand2",
                highlightthickness=1, highlightbackground=BORDE,
                highlightcolor=AZUL, pady=8
            ).grid(
                row=0, column=i, sticky="ew",
                padx=(0 if i == 0 else 3, 0 if i == 2 else 3)
            )

        etiqueta_campo("Motivo del justificante", 7, 0)
        etiqueta_campo("Evidencia (imagen)", 7, 1)

        motivo = tk.Text(
            panel_just,
            height=6,
            font=("Segoe UI", 10),
            bg=CAMPO,
            fg=TEXTO,
            relief="flat",
            bd=0,
            wrap="word",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=BORDE,
            highlightcolor=AZUL,
            insertbackground=TEXTO
        )
        motivo.grid(row=8, column=0, sticky="nsew", padx=pad(0), pady=(0, 20))

        caja_imagen = tk.Frame(
            panel_just, bg=FONDO_VACIO,
            highlightbackground=BORDE_VACIO, highlightthickness=1
        )
        caja_imagen.grid(row=8, column=1, sticky="nsew", padx=pad(1), pady=(0, 20))

        centro = tk.Frame(caja_imagen, bg=FONDO_VACIO)
        centro.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            centro, text="IMAGEN", bg=FONDO_VACIO, fg=AZUL,
            font=("Segoe UI", 14, "bold")
        ).pack()

        tk.Label(
            centro, text="La evidencia se mostrará aquí", bg=FONDO_VACIO,
            fg=SECUNDARIO, font=("Segoe UI", 9)
        ).pack(pady=(3, 0))

        tk.Frame(panel_just, bg=BORDE, height=1).grid(
            row=9, column=0, columnspan=2, sticky="ew", pady=(0, 18)
        )

        def limpiar():
            alumno_combo.set("")
            fecha_entry.set(date.today())
            tipo_var.set("Enfermedad")
            motivo.delete("1.0", "end")

        def registrar():
            alumno = alumno_combo.get()
            fecha = fecha_entry.get().strip()
            descripcion = motivo.get("1.0", "end").strip()

            if alumno not in ALUMNOS:
                messagebox.showwarning("Dato faltante", "Busca y selecciona un alumno de la lista.")
                return

            if not fecha or not descripcion:
                messagebox.showwarning(
                    "Dato faltante",
                    "Escribe la fecha y el motivo del justificante."
                )
                return

            justificantes.append({
                "alumno": alumno,
                "grupo": GRUPO_MAESTRO,
                "fecha": fecha,
                "tipo": tipo_var.get(),
                "motivo": descripcion
            })

            messagebox.showinfo(
                "Registro exitoso",
                f"El justificante de {alumno} se registró correctamente."
            )
            limpiar()

        acciones = tk.Frame(panel_just, bg=BLANCO)
        acciones.grid(row=10, column=0, columnspan=2, sticky="e")

        tk.Button(
            acciones, text="Limpiar", command=limpiar,
            bg=CAMPO, fg=TEXTO, activebackground=BORDE,
            activeforeground=TEXTO, font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0, cursor="hand2", padx=18, pady=11,
            highlightthickness=1, highlightbackground=BORDE
        ).pack(side="left", padx=(0, 10))

        boton_padre(
            acciones, "Guardar justificante", registrar
        ).pack(side="left")

    def pantalla_incidencias():
        encabezado(
            "Registro de incidencias",
            "Documenta situaciones académicas, de conducta u otros incidentes."
        )

        GAP = 12  

        panel_inc = tarjeta(area_contenido, 24)
        panel_inc.pack(fill="x")
        panel_inc.columnconfigure(0, weight=1, uniform="col")
        panel_inc.columnconfigure(1, weight=1, uniform="col")

        def pad(col):
            return (0, GAP) if col == 0 else (GAP, 0)

        def etiqueta_campo(texto, fila, col, ancho=1):
            tk.Label(
                panel_inc, text=texto.upper(), bg=BLANCO, fg=SECUNDARIO,
                font=("Segoe UI", 8, "bold"), anchor="w", padx=0, bd=0
            ).grid(
                row=fila, column=col, columnspan=ancho, sticky="w",
                padx=pad(col) if ancho == 1 else 0, pady=(0, 6)
            )

        tk.Label(
            panel_inc, text="Información de la incidencia", bg=BLANCO,
            fg=MARINO, font=("Segoe UI", 14, "bold"), anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        tk.Label(
            panel_inc,
            text="Completa los datos del alumno y describe lo ocurrido.",
            bg=BLANCO, fg=SECUNDARIO, font=("Segoe UI", 9), anchor="w"
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 14))

        tk.Frame(panel_inc, bg=BORDE, height=1).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(0, 18)
        )

        etiqueta_campo("Alumno", 3, 0)
        alumno_combo = BuscadorAlumno(
            panel_inc, ALUMNOS, fuente=("Segoe UI", 10), fondo=CAMPO,
            borde=BORDE, acento=AZUL, acento_claro=AZUL_SUAVE,
            texto=TEXTO, suave=SECUNDARIO, ipady=8
        )
        alumno_combo.grid(row=4, column=0, sticky="ew", padx=pad(0), pady=(0, 18))

        etiqueta_campo("Grupo", 3, 1)
        grupo = crear_entrada(panel_inc, 32)
        grupo.grid(row=4, column=1, sticky="ew", padx=pad(1), pady=(0, 18), ipady=8)
        grupo.insert(0, GRUPO_MAESTRO)
        grupo.config(
            state="readonly", readonlybackground="#EEF2F7", fg=SECUNDARIO
        )

        etiqueta_campo("Fecha de la incidencia", 5, 0)
        fecha_entry = SelectorFecha(
            panel_inc, fuente=("Segoe UI", 10), fondo=CAMPO, borde=BORDE,
            acento=AZUL, acento_claro=AZUL_SUAVE, texto=TEXTO,
            suave=SECUNDARIO, ipady=8
        )
        fecha_entry.grid(row=6, column=0, sticky="ew", padx=pad(0), pady=(0, 18))

        etiqueta_campo("Tipo de incidencia", 5, 1)
        tipo_combo = crear_combo(
            panel_inc, ["Conducta", "Académico", "Incidente", "Otro"], 32
        )
        tipo_combo.grid(row=6, column=1, sticky="ew", padx=pad(1), pady=(0, 18))
        tipo_combo.set("Selecciona un tipo")

        etiqueta_campo("Prioridad", 7, 0, 2)
        prioridad_var = tk.StringVar(value="Media")
        prioridad_frame = tk.Frame(panel_inc, bg=BLANCO)
        prioridad_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 18))

        colores_prioridad = [
            ("Baja", VERDE_SUAVE),
            ("Media", NARANJA_SUAVE),
            ("Alta", ROJO_SUAVE)
        ]
        for i, (nombre_p, color_p) in enumerate(colores_prioridad):
            prioridad_frame.columnconfigure(i, weight=1, uniform="prio")
            tk.Radiobutton(
                prioridad_frame, text=nombre_p, variable=prioridad_var,
                value=nombre_p, indicatoron=0, bg=CAMPO, fg=TEXTO,
                selectcolor=color_p, activebackground=color_p,
                activeforeground=TEXTO, font=("Segoe UI", 10),
                relief="flat", bd=0, cursor="hand2",
                highlightthickness=1, highlightbackground=BORDE,
                highlightcolor=AZUL, pady=8
            ).grid(
                row=0, column=i, sticky="ew",
                padx=(0 if i == 0 else 3, 0 if i == 2 else 3)
            )

        etiqueta_campo("Descripción de la incidencia", 9, 0, 2)
        motivo = tk.Text(
            panel_inc,
            height=6,
            font=("Segoe UI", 10),
            bg=CAMPO,
            fg=TEXTO,
            relief="flat",
            bd=0,
            wrap="word",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=BORDE,
            highlightcolor=AZUL,
            insertbackground=TEXTO
        )
        motivo.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(0, 20))

        tk.Frame(panel_inc, bg=BORDE, height=1).grid(
            row=11, column=0, columnspan=2, sticky="ew", pady=(0, 18)
        )

        def limpiar():
            alumno_combo.set("")
            fecha_entry.set(date.today())
            tipo_combo.set("Selecciona un tipo")
            prioridad_var.set("Media")
            motivo.delete("1.0", "end")

        def registrar():
            alumno = alumno_combo.get()
            tipo = tipo_combo.get()
            fecha = fecha_entry.get().strip()
            descripcion = motivo.get("1.0", "end").strip()

            if alumno not in ALUMNOS:
                messagebox.showwarning(
                    "Dato faltante", "Busca y selecciona un alumno de la lista."
                )
                return

            if tipo not in ["Conducta", "Académico", "Incidente", "Otro"]:
                messagebox.showwarning(
                    "Dato faltante",
                    "Selecciona el tipo de incidencia."
                )
                return

            if not fecha:
                messagebox.showwarning(
                    "Dato faltante",
                    "Selecciona la fecha de la incidencia."
                )
                return

            if not descripcion:
                messagebox.showwarning(
                    "Dato faltante",
                    "Escribe la descripción de la incidencia."
                )
                return

            incidencias.append({
                "alumno": alumno,
                "grupo": GRUPO_MAESTRO,
                "tipo": tipo,
                "prioridad": prioridad_var.get(),
                "motivo": descripcion,
                "fecha": fecha
            })

            messagebox.showinfo(
                "Registro exitoso",
                f"La incidencia de {alumno} se registró correctamente."
            )
            limpiar()

        acciones = tk.Frame(panel_inc, bg=BLANCO)
        acciones.grid(row=12, column=0, columnspan=2, sticky="e")

        tk.Button(
            acciones, text="Limpiar", command=limpiar,
            bg=CAMPO, fg=TEXTO, activebackground=BORDE,
            activeforeground=TEXTO, font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0, cursor="hand2", padx=18, pady=11,
            highlightthickness=1, highlightbackground=BORDE
        ).pack(side="left", padx=(0, 10))

        boton_padre(
            acciones, "Guardar incidencia", registrar
        ).pack(side="left")

    def pantalla_perfil():
        encabezado(
            "Perfil del docente",
            "Información de la cuenta y datos asignados."
        )

        panel_perfil = tarjeta(area_contenido, 24)
        panel_perfil.pack(fill="x", pady=(0, 18))

        superior = tk.Frame(panel_perfil, bg=BLANCO)
        superior.pack(fill="x")

        avatar = tk.Frame(
            superior,
            bg=AZUL_SUAVE,
            width=86,
            height=86
        )
        avatar.pack(side="left", padx=(0, 18))
        avatar.pack_propagate(False)

        iniciales = "".join(
            parte[0] for parte in NOMBRE_MAESTRO.split()[:2]
        )

        tk.Label(
            avatar,
            text=iniciales,
            bg=AZUL_SUAVE,
            fg=AZUL,
            font=("Segoe UI", 24, "bold")
        ).pack(expand=True)

        datos = tk.Frame(superior, bg=BLANCO)
        datos.pack(side="left", fill="both", expand=True)

        tk.Label(
            datos,
            text=NOMBRE_MAESTRO,
            bg=BLANCO,
            fg=MARINO,
            font=("Segoe UI", 19, "bold")
        ).pack(anchor="w", pady=(5, 4))

        tk.Label(
            datos,
            text="Docente de educación primaria",
            bg=BLANCO,
            fg=SECUNDARIO,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(0, 10))

        tk.Label(
            datos,
            text="CUENTA ACTIVA",
            bg=VERDE_SUAVE,
            fg=VERDE,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=5
        ).pack(anchor="w")

        separador(panel_perfil)

        columnas = tk.Frame(panel_perfil, bg=BLANCO)
        columnas.pack(fill="x")

        laboral = tk.Frame(
            columnas,
            bg=CAMPO,
            padx=18,
            pady=18,
            highlightbackground=BORDE,
            highlightthickness=1
        )
        laboral.pack(side="left", fill="both", expand=True, padx=(0, 8))

        emergencia = tk.Frame(
            columnas,
            bg=CAMPO,
            padx=18,
            pady=18,
            highlightbackground=BORDE,
            highlightthickness=1
        )
        emergencia.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(
            laboral,
            text="INFORMACIÓN LABORAL",
            bg=CAMPO,
            fg=AZUL,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 12))

        datos_laborales = [
            ("Cargo", "Docente"),
            ("Grupo asignado", GRUPO_MAESTRO),
            ("Plantel", PLANTEL),
            ("Turno", "Matutino"),
            ("Horario", "7:30 a. m. - 12:30 p. m.")
        ]

        for titulo, valor in datos_laborales:
            tk.Label(
                laboral,
                text=titulo,
                bg=CAMPO,
                fg=SECUNDARIO,
                font=("Segoe UI", 9)
            ).pack(anchor="w", pady=(6, 2))

            tk.Label(
                laboral,
                text=valor,
                bg=CAMPO,
                fg=TEXTO,
                font=("Segoe UI", 10, "bold"),
                wraplength=300,
                justify="left"
            ).pack(anchor="w")

        tk.Label(
            emergencia,
            text="CONTACTO DE EMERGENCIA",
            bg=CAMPO,
            fg=VERDE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 12))

        datos_emergencia = [
            ("Nombre", "María García"),
            ("Relación", "Familiar"),
            ("Teléfono", "55 8765 4321")
        ]

        for titulo, valor in datos_emergencia:
            tk.Label(
                emergencia,
                text=titulo,
                bg=CAMPO,
                fg=SECUNDARIO,
                font=("Segoe UI", 9)
            ).pack(anchor="w", pady=(6, 2))

            tk.Label(
                emergencia,
                text=valor,
                bg=CAMPO,
                fg=TEXTO,
                font=("Segoe UI", 10, "bold")
            ).pack(anchor="w")

        tk.Label(
            emergencia,
            text="Para modificar estos datos, solicita una actualización a la dirección escolar.",
            bg=CAMPO,
            fg=SECUNDARIO,
            font=("Segoe UI", 9),
            wraplength=300,
            justify="left"
        ).pack(anchor="w", pady=(18, 0))

    def cerrar_sesion_maestro():
        if messagebox.askyesno("Cerrar sesión", "¿Deseas volver al inicio de sesión?"):
            root.unbind_all("<MouseWheel>")
            root.unbind_all("<Button-4>")
            root.unbind_all("<Button-5>")
            root.destroy()
            ventana.deiconify()
            ventana.state("zoomed")
            entrada_usuario.delete(0, tk.END)
            entrada_contrasena.delete(0, tk.END)
            entrada_codigo.delete(0, tk.END)
            var_codigo.set(False)
            mostrar_codigo()
            entrada_usuario.focus_set()

    def crear_app():
        nonlocal area_contenido, botones_menu, lienzo_contenido

        for widget in root.winfo_children():
            widget.destroy()

        botones_menu = {}

        barra_lateral = tk.Frame(root, bg=MARINO, width=235)
        barra_lateral.pack(side="left", fill="y")
        barra_lateral.pack_propagate(False)

        def ajustar_ancho_docente(event=None):
            ancho_ventana = root.winfo_width()
            barra_lateral.config(width=145 if ancho_ventana < 700 else (170 if ancho_ventana < 900 else 235))

        root.bind("<Configure>", ajustar_ancho_docente, add="+")

        tk.Label(
            barra_lateral,
            text="GESTIÓN ESCOLAR",
            bg=MARINO,
            fg="#9EBBFF",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=22, pady=(28, 4))

        tk.Label(
            barra_lateral,
            text="Panel docente",
            bg=MARINO,
            fg=BLANCO,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=22, pady=(0, 24))

        tk.Frame(
            barra_lateral,
            bg="#304666",
            height=1
        ).pack(fill="x", padx=18, pady=(0, 18))

        tk.Label(
            barra_lateral,
            text="MENÚ PRINCIPAL",
            bg=MARINO,
            fg="#91A4BF",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", padx=22, pady=(0, 10))

        opciones = [
            ("Inicio", pantalla_inicio),
            ("Asistencias", pantalla_asistencias),
            ("Justificantes", pantalla_justificantes),
            ("Incidencias", pantalla_incidencias),
            ("Mi perfil", pantalla_perfil)
        ]

        for nombre, funcion in opciones:
            boton = tk.Button(
                barra_lateral,
                text="   " + nombre,
                command=lambda n=nombre, f=funcion: abrir_pantalla(n, f),
                bg=MARINO,
                fg="#C8D3E2",
                activebackground=MARINO_CLARO,
                activeforeground=BLANCO,
                font=("Segoe UI", 10),
                anchor="w",
                relief="flat",
                bd=0,
                padx=16,
                pady=13,
                cursor="hand2"
            )
            boton.pack(fill="x", padx=10, pady=3)
            botones_menu[nombre] = boton

        tk.Frame(
            barra_lateral,
            bg="#304666",
            height=1
        ).pack(fill="x", padx=18, pady=(22, 16))

        tk.Label(
            barra_lateral,
            text="SESIÓN ACTIVA",
            bg=MARINO,
            fg="#91A4BF",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", padx=22)

        tk.Label(
            barra_lateral,
            text=NOMBRE_MAESTRO,
            bg=MARINO,
            fg=BLANCO,
            font=("Segoe UI", 10, "bold"),
            wraplength=185,
            justify="left"
        ).pack(anchor="w", padx=22, pady=(7, 3))

        tk.Label(
            barra_lateral,
            text=f"Grupo {GRUPO_MAESTRO}",
            bg=MARINO,
            fg="#AABBD0",
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=22)

        tk.Button(
            barra_lateral,
            text="Cerrar sesión",
            command=cerrar_sesion_maestro,
            bg="#D94F54",
            fg=BLANCO,
            activebackground="#B9383E",
            activeforeground=BLANCO,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            pady=11
        ).pack(side="bottom", fill="x", padx=12, pady=18)

        principal = tk.Frame(root, bg=FONDO)
        principal.pack(side="left", fill="both", expand=True)

        barra_superior = tk.Frame(
            principal,
            bg=BLANCO,
            height=66,
            highlightbackground=BORDE,
            highlightthickness=1
        )
        barra_superior.pack(fill="x")
        barra_superior.pack_propagate(False)

        tk.Label(
            barra_superior,
            text=PLANTEL,
            bg=BLANCO,
            fg=MARINO,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=28)

        tk.Label(
            barra_superior,
            text=date.today().strftime("%d/%m/%Y"),
            bg=BLANCO,
            fg=SECUNDARIO,
            font=("Segoe UI", 10)
        ).pack(side="right", padx=28)

        zona_desplazable = tk.Frame(principal, bg=FONDO)
        zona_desplazable.pack(fill="both", expand=True)

        lienzo_contenido = tk.Canvas(
            zona_desplazable,
            bg=FONDO,
            highlightthickness=0,
            borderwidth=0
        )
        barra_contenido = ttk.Scrollbar(
            zona_desplazable,
            orient="vertical",
            command=lienzo_contenido.yview
        )
        lienzo_contenido.configure(yscrollcommand=barra_contenido.set)
        barra_contenido.pack(side="right", fill="y")
        lienzo_contenido.pack(side="left", fill="both", expand=True)

        area_contenido = tk.Frame(
            lienzo_contenido,
            bg=FONDO,
            padx=12,
            pady=16
        )
        ventana_contenido = lienzo_contenido.create_window(
            (0, 0), window=area_contenido, anchor="nw"
        )

        estado_barra_docente = {"visible": True, "pendiente": False}

        def revisar_barra_docente():
            estado_barra_docente["pendiente"] = False
            try:
                if not lienzo_contenido.winfo_exists():
                    return
                necesita = (
                    area_contenido.winfo_reqheight()
                    > lienzo_contenido.winfo_height() > 1
                )
            except tk.TclError:
                return
            if necesita and not estado_barra_docente["visible"]:
                barra_contenido.pack(
                    side="right", fill="y", before=lienzo_contenido
                )
                estado_barra_docente["visible"] = True
            elif not necesita and estado_barra_docente["visible"]:
                barra_contenido.pack_forget()
                estado_barra_docente["visible"] = False

        def actualizar_region_docente(event=None):
            lienzo_contenido.configure(
                scrollregion=lienzo_contenido.bbox("all")
            )
            if not estado_barra_docente["pendiente"]:
                estado_barra_docente["pendiente"] = True
                lienzo_contenido.after_idle(revisar_barra_docente)

        def ajustar_lienzo_docente(event):
            lienzo_contenido.itemconfigure(
                ventana_contenido, width=event.width
            )
            actualizar_region_docente()

        area_contenido.bind("<Configure>", actualizar_region_docente)
        lienzo_contenido.bind("<Configure>", ajustar_lienzo_docente)

        def adaptar_espaciado_docente(event=None):
            ancho = root.winfo_width()
            if ancho < 760:
                area_contenido.configure(padx=10, pady=12)
            elif ancho < 1000:
                area_contenido.configure(padx=18, pady=18)
            else:
                area_contenido.configure(padx=28, pady=25)

        root.bind("<Configure>", adaptar_espaciado_docente, add="+")

        def desplazar_docente(event):
            desplazar_contenido_con_rueda(event, lienzo_contenido)
            return "break"

        def desplazar_docente_linux_arriba(event):
            desplazar_contenido_con_rueda(event, lienzo_contenido)
            return "break"

        def desplazar_docente_linux_abajo(event):
            desplazar_contenido_con_rueda(event, lienzo_contenido)
            return "break"

        root.bind_all("<MouseWheel>", desplazar_docente)
        root.bind_all("<Button-4>", desplazar_docente_linux_arriba)
        root.bind_all("<Button-5>", desplazar_docente_linux_abajo)

        actualizar_menu("Inicio")
        pantalla_inicio()

    crear_app()
    root.protocol("WM_DELETE_WINDOW", cerrar_sesion_maestro)


def abrir_panel(usuario, rol):
    panel = tk.Toplevel(ventana)
    if rol == "Director":
        abrir_panel_director(panel)
    else:
        abrir_panel_maestro(panel, usuario)


def mostrar_codigo():
    """Prepara el nombre fijo de la cuenta del director."""
    if var_codigo.get():
        entrada_usuario.delete(0, tk.END)
        entrada_usuario.insert(0, "Director")
        entrada_codigo.pack_forget()
        entrada_codigo.delete(0, tk.END)
    else:
        entrada_codigo.pack_forget()
        entrada_codigo.delete(0, tk.END)


ventana = tk.Tk()
ventana.title("Sistema de control escolar")
ventana.geometry("1100x700")
ventana.minsize(620, 430)
ventana.resizable(True, True)
ventana.configure(bg=AZUL_OSCURO)
ventana.state("zoomed")

contenedor = tk.Frame(ventana, bg=AZUL_OSCURO)
contenedor.pack(fill="both", expand=True, padx=20, pady=20)

izquierda = tk.Frame(
    contenedor,
    bg=AZUL_OSCURO,
    width=400
)
izquierda.pack(side="left", fill="both")
izquierda.pack_propagate(False)


def ajustar_login(event=None):
    ancho = ventana.winfo_width()
    if ancho < 800:
        izquierda.config(width=230)
    elif ancho < 1000:
        izquierda.config(width=300)
    else:
        izquierda.config(width=400)


ventana.bind("<Configure>", ajustar_login, add="+")

espacio_imagen = tk.Frame(
    izquierda,
    bg=TARJETA,
    highlightbackground=BORDE,
    highlightthickness=1
)
espacio_imagen.pack(
    fill="both",
    expand=True,
    padx=28,
    pady=(28, 20)
)

tk.Label(
    espacio_imagen,
    text="IMAGEN DEL PROYECTO",
    font=("Arial", 12, "bold"),
    bg=TARJETA,
    fg=SUAVE
).place(relx=0.5, rely=0.5, anchor="center")

tk.Label(
    izquierda,
    text="SISTEMA DE\nALERTA TEMPRANA\nPRIMARIA NEZAHUALCOYOTL",
    font=("Arial", 15, "bold"),
    bg=AZUL_OSCURO,
    fg=BLANCO,
    justify="left"
).pack(anchor="w", padx=28, pady=(0, 12))

tk.Frame(
    izquierda,
    bg=AZUL,
    height=4,
    width=70
).pack(anchor="w", padx=28, pady=(0, 15))

tk.Label(
    izquierda,
    text="Plataforma para la gestión y el\n"
         "seguimiento de las actividades escolares.",
    font=("Arial", 11),
    bg=AZUL_OSCURO,
    fg=SUAVE,
    justify="left"
).pack(anchor="w", padx=28, pady=(0, 15))

tk.Label(
    izquierda,
    text="USO EXCLUSIVO DEL PERSONAL ESCOLAR",
    font=("Arial", 8, "bold"),
    bg=AZUL_OSCURO,
    fg=SUAVE
).pack(anchor="w", padx=28, pady=(0, 22))

derecha = tk.Frame(
    contenedor,
    bg=TARJETA
)
derecha.pack(side="left", fill="both", expand=True)

formulario = tk.Frame(
    derecha,
    bg=TARJETA
)
formulario.place(
    relx=0.5,
    rely=0.5,
    anchor="center",
    relwidth=0.78
)

tk.Label(
    formulario,
    text="Bienvenido",
    font=("Arial", 27, "bold"),
    bg=TARJETA,
    fg=BLANCO
).pack(anchor="w", pady=(0, 5))

tk.Label(
    formulario,
    text="Inicia sesión para continuar",
    font=("Arial", 11),
    bg=TARJETA,
    fg=SUAVE
).pack(anchor="w", pady=(0, 28))


def crear_etiqueta(texto):
    tk.Label(
        formulario,
        text=texto,
        font=("Arial", 9, "bold"),
        bg=TARJETA,
        fg="#cbd5e1"
    ).pack(anchor="w", pady=(0, 7))


def crear_entrada(mostrar=None):
    campo = tk.Entry(
        formulario,
        font=("Arial", 11),
        bg=CAMPO,
        fg=BLANCO,
        insertbackground=BLANCO,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDE,
        highlightcolor=AZUL,
        show=mostrar or ""
    )
    campo.pack(fill="x", ipady=10, pady=(0, 18))
    return campo


crear_etiqueta("USUARIO")
entrada_usuario = crear_entrada()

crear_etiqueta("CONTRASEÑA")
entrada_contrasena = crear_entrada("*")

var_codigo = tk.BooleanVar(value=False)

tk.Checkbutton(
    formulario,
    text="Registrar cuenta de dirección",
    variable=var_codigo,
    command=mostrar_codigo,
    bg=TARJETA,
    fg=SUAVE,
    activebackground=TARJETA,
    activeforeground=BLANCO,
    selectcolor=CAMPO,
    font=("Arial", 9),
    cursor="hand2"
).pack(anchor="w", pady=(0, 8))

entrada_codigo = tk.Entry(
    formulario,
    font=("Arial", 11),
    bg=CAMPO,
    fg=BLANCO,
    insertbackground=BLANCO,
    relief="flat",
    highlightthickness=1,
    highlightbackground=BORDE,
    show="*"
)

tk.Button(
    formulario,
    text="Iniciar sesión",
    command=entrar,
    font=("Arial", 11, "bold"),
    bg=AZUL,
    fg=AZUL_OSCURO,
    activebackground="#33d0ff",
    activeforeground=AZUL_OSCURO,
    relief="flat",
    cursor="hand2",
    pady=12
).pack(fill="x", pady=(10, 18))

tk.Frame(
    formulario,
    bg=BORDE,
    height=1
).pack(fill="x", pady=(0, 17))

tk.Label(
    formulario,
    text="¿Aun no tienes una cuenta?",
    font=("Arial", 10),
    bg=TARJETA,
    fg=SUAVE
).pack(anchor="w", pady=(0, 9))

tk.Button(
    formulario,
    text="Crear cuenta",
    command=registrar_usuario,
    font=("Arial", 10, "bold"),
    bg=BOTON_SECUNDARIO,
    fg=SUAVE,
    activebackground="#2a3b70",
    activeforeground=BLANCO,
    relief="flat",
    cursor="hand2",
    pady=11
).pack(fill="x")

ventana.mainloop()
#mariana hizo base de datos - coming
