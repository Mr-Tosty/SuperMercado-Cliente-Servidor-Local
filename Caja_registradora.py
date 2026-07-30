import sqlite3
import os
import cv2
from pyzbar.pyzbar import decode
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import time
import tempfile
import webbrowser
import winsound
import pyttsx3

os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

# --- COLORES ESTILO OXXO
COLOR_FONDO = "#00723F"      # Verde oscuro de fondo
COLOR_HEADER = "#00522B"     # Verde más oscuro para cabecera
COLOR_ITEM_BG = "#00A859"    # Verde OXXO para items
COLOR_TOTAL = "#FFB300"      # Amarillo OXXO
COLOR_TEXTO = "#FFFFFF"      # Blanco
COLOR_TEXTO_OSCURO = "#000"  # Negro

class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Login de Administrador - OXXO")
        self.root.geometry("400x300")
        self.root.configure(bg=COLOR_FONDO)
        
        # Centrar ventana
        self.root.eval('tk::PlaceWindow . center')
        
        tk.Label(self.root, text="INICIAR SESIÓN", font=("Arial", 20, "bold"), bg=COLOR_FONDO, fg=COLOR_TOTAL).pack(pady=30)
        
        tk.Label(self.root, text="Usuario:", font=("Arial", 14), bg=COLOR_FONDO, fg=COLOR_TEXTO).pack()
        self.entry_user = tk.Entry(self.root, font=("Arial", 14))
        self.entry_user.pack(pady=5)
        
        tk.Label(self.root, text="Contraseña:", font=("Arial", 14), bg=COLOR_FONDO, fg=COLOR_TEXTO).pack()
        self.entry_pass = tk.Entry(self.root, font=("Arial", 14), show="*")
        self.entry_pass.pack(pady=5)
        
        tk.Button(self.root, text="ENTRAR", font=("Arial", 14, "bold"), bg=COLOR_TOTAL, fg=COLOR_TEXTO_OSCURO, 
                  command=self.verificar_login).pack(pady=20)

    def verificar_login(self):
        usuario = self.entry_user.get()
        password = self.entry_pass.get()
        
        if usuario == "admin" and password == "admin4545superadmin":
            self.root.destroy()
            iniciar_app()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")

class CajaRegistradoraAPP:
    def __init__(self, root):
        self.root = root
        self.root.title("AUTOCOBRO - OXXO")
        self.root.geometry("1024x768")
        self.root.configure(bg=COLOR_FONDO)
        
        self.inicializar_bd()
        self.carrito = []  # Lista de diccionarios con los productos a cobrar
        self.ultimo_scan = 0 # Para evitar escanear múltiples veces por segundo
        
        self.construir_interfaz()
        
        # Inicializar cámara
        self.cap = cv2.VideoCapture(0)
        self.actualizar_camara()

    def inicializar_bd(self):
        # Obtenemos la ruta absoluta de la carpeta donde está este script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'caja_registradora.db')
        
        # Conectamos obligatoriamente al archivo que está junto al script
        self.conexion = sqlite3.connect(db_path)
        self.cursor = self.conexion.cursor()
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            codigo_barras TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            descripcion TEXT NOT NULL
        )''')
        # Insertar algunos productos de prueba si está vacía
        self.cursor.execute("SELECT COUNT(*) FROM productos")
        if self.cursor.fetchone()[0] == 0:
            productos = [
                ('7501000111222', 'Galletas Chokis', 18.50, 'Galletas chocolate 90g'),
                ('758104008193', 'Agua Bonafont 1L', 20.00, 'Botella de agua purificada')
            ]
            self.cursor.executemany("INSERT INTO productos VALUES (?,?,?,?)", productos)
        self.conexion.commit()

    def construir_interfaz(self):
        # HEADER
        header = tk.Frame(self.root, bg=COLOR_HEADER, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="AUTOCOBRO", font=("Arial", 28, "bold"), bg=COLOR_HEADER, fg=COLOR_TEXTO).pack(side="left", padx=20, pady=10)
        tk.Label(header, text="Bienvenidos", font=("Arial", 16), bg=COLOR_HEADER, fg=COLOR_TEXTO).pack(side="left", pady=25)
        
        # CUERPO
        body = tk.Frame(self.root, bg=COLOR_FONDO)
        body.pack(fill="both", expand=True, padx=20, pady=20)
        
        # --- PANEL IZQUIERDO (Lista de artículos) ---
        left_panel = tk.Frame(body, bg=COLOR_FONDO)
        left_panel.pack(side="left", fill="both", expand=True)
        
        tk.Label(left_panel, text="ARTÍCULOS ESCANEADOS:", font=("Arial", 18, "bold"), bg=COLOR_FONDO, fg=COLOR_TOTAL).pack(anchor="w", pady=(0, 10))
        
        self.canvas_items = tk.Canvas(left_panel, bg=COLOR_HEADER, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(left_panel, orient="vertical", command=self.canvas_items.yview)
        self.frame_items = tk.Frame(self.canvas_items, bg=COLOR_HEADER)
        
        self.canvas_items.create_window((0, 0), window=self.frame_items, anchor="nw", width=550)
        self.canvas_items.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas_items.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.frame_items.bind("<Configure>", lambda e: self.canvas_items.configure(scrollregion=self.canvas_items.bbox("all")))
        
        # --- PANEL DERECHO (Cámara, Imagen, Controles y Total) ---
        right_panel = tk.Frame(body, bg=COLOR_FONDO, width=380)
        right_panel.pack(side="right", fill="y", padx=(20, 0))
        right_panel.pack_propagate(False)
        
        # Área de cámara e imagen del producto
        media_frame = tk.Frame(right_panel, bg=COLOR_FONDO)
        media_frame.pack(fill="x", pady=(0, 10))
        
        cam_frame = tk.Frame(media_frame, bg="black", width=180, height=150)
        cam_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        cam_frame.pack_propagate(False)
        self.lbl_video = tk.Label(cam_frame, bg="black")
        self.lbl_video.pack(fill="both", expand=True)
        
        try:
            # Busca la imagen en la carpeta 'imagenes'
            img_icono = Image.open("Icono.png").resize((180, 150))
            img_icono_tk = ImageTk.PhotoImage(image=img_icono)
            self.lbl_video.configure(image=img_icono_tk)
            self.lbl_video.image = img_icono_tk # Mantiene la referencia
        except Exception:
            self.lbl_video.configure(text="Icono.png no\nencontrado", fg="white")
        
        self.lbl_imagen_actual = tk.Label(media_frame, bg="white", text="Escanea un\nProducto", font=("Arial", 12))
        self.lbl_imagen_actual.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # Controles y Botones
        control_frame = tk.Frame(right_panel, bg=COLOR_FONDO)
        control_frame.pack(fill="x", pady=5)
        
        self.entry_manual = tk.Entry(control_frame, font=("Arial", 16))
        self.entry_manual.pack(fill="x", pady=5)
        
        # Vincular la tecla "Enter" de un escáner físico a la nueva función
        self.entry_manual.bind("<Return>", lambda event: self.intentar_escanear())
        
        # Fila de botones 1
        btn_frame1 = tk.Frame(control_frame, bg=COLOR_FONDO)
        btn_frame1.pack(fill="x", pady=2)
        
        # Guardamos la referencia del botón en self.btn_ingresar para poder bloquearlo
        self.btn_ingresar = tk.Button(btn_frame1, text="Buscar / Ingresar", font=("Arial", 10, "bold"), bg=COLOR_TOTAL, 
                                      command=self.intentar_escanear)
        self.btn_ingresar.pack(side="left", expand=True, fill="x", padx=2)
        
        tk.Button(btn_frame1, text="Registrar en BD", font=("Arial", 10, "bold"), bg="#00A859", fg="white", 
                  command=lambda: self.registrar_nuevo_producto(self.entry_manual.get())).pack(side="right", expand=True, fill="x", padx=2)
        
        # Fila de botones 2
        btn_frame2 = tk.Frame(control_frame, bg=COLOR_FONDO)
        btn_frame2.pack(fill="x", pady=2)
        tk.Button(btn_frame2, text="Ver Base de Datos", font=("Arial", 10, "bold"), bg="#56B3C2", 
                  command=self.ver_base_datos).pack(fill="x", padx=2)
        
        # Caja de Total
        total_frame = tk.Frame(right_panel, bg=COLOR_TOTAL, bd=2, relief="solid")
        total_frame.pack(fill="x", pady=15)
        tk.Label(total_frame, text="TOTAL A PAGAR:", font=("Arial", 16, "bold"), bg=COLOR_TOTAL).pack(anchor="w", padx=10, pady=(10,0))
        self.lbl_total = tk.Label(total_frame, text="$0.00", font=("Arial", 40, "bold"), bg=COLOR_TOTAL)
        self.lbl_total.pack(anchor="w", padx=10, pady=(0, 10))
        
        self.lbl_impuestos = tk.Label(total_frame, text="(Incluye 16% IVA)", font=("Arial", 10), bg=COLOR_TOTAL)
        self.lbl_impuestos.pack(anchor="e", padx=10, pady=(0, 5))
        
        # Botón Pagar
        tk.Button(right_panel, text="PAGAR AHORA", font=("Arial", 20, "bold"), bg="#E1251B", fg="white",
                  command=self.mostrar_opciones_pago).pack(fill="x", pady=5)
        
    def actualizar_camara(self):
        if self.cap.isOpened():
            exito, frame = self.cap.read()
            if exito:
                codigos_detectados = decode(frame)
                for codigo_leido in codigos_detectados:
                    codigo = codigo_leido.data.decode('utf-8')
                    # Evitar múltiples lecturas del mismo código en menos de 2 segundos
                    if time.time() - self.ultimo_scan > 2:
                        self.procesar_codigo(codigo)
                        self.ultimo_scan = time.time()

                #frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                #frame_rgb = cv2.resize(frame_rgb, (350, 260))
                #img = Image.fromarray(frame_rgb)
                #imgtk = ImageTk.PhotoImage(image=img)
                #self.lbl_video.imgtk = imgtk
                #self.lbl_video.configure(image=imgtk)
                
        self.root.after(50, self.actualizar_camara)

    def intentar_escanear(self):
        # Si el escáner está en sus 5 segundos de bloqueo, se cancela la acción
        if getattr(self, 'escaneo_bloqueado', False):
            return
            
        codigo = self.entry_manual.get().strip()
        
        # Validar si el campo de texto está vacío o hubo un error de lectura
        if not codigo:
            messagebox.showwarning("Error de Escaneo", "El producto no ha sido escaneado correctamente, inténtelo de nuevo.")
            return
            
        # Bloquear el botón de ingreso y las lecturas físicas para evitar duplicados
        self.escaneo_bloqueado = True
        self.btn_ingresar.config(state="disabled", text="Espere (5s)...")
        
        # Programar el desbloqueo después de 5000 milisegundos (5 segundos)
        self.root.after(5000, self.desbloquear_escaneo)
        
        # Procesar el código del producto
        self.procesar_codigo(codigo)

    def desbloquear_escaneo(self):
        # Habilitar nuevamente el botón
        self.escaneo_bloqueado = False
        self.btn_ingresar.config(state="normal", text="Buscar / Ingresar")
        
        self.entry_manual.delete(0, tk.END)

    def procesar_codigo(self, codigo):
        # Busca en la BD
        self.cursor.execute("SELECT nombre, precio, descripcion FROM productos WHERE codigo_barras = ?", (codigo,))
        producto = self.cursor.fetchone()
        
        extensiones = ['.png', '.jpg', '.jpeg']
        ruta_img_encontrada = None
        for ext in extensiones:
            ruta_prueba = f"imagenes/{codigo}{ext}"
            if os.path.exists(ruta_prueba):
                ruta_img_encontrada = ruta_prueba
                break
        
        if producto:
            if ruta_img_encontrada:
                img_prod = Image.open(ruta_img_encontrada).resize((180, 150))
                img_tk = ImageTk.PhotoImage(img_prod)
                self.lbl_imagen_actual.configure(image=img_tk, text="")
                self.lbl_imagen_actual.image = img_tk
            else:
                self.lbl_imagen_actual.configure(image="", text="Imagen no\nencontrada")

            try:
                precio_float = float(producto[1])
            except (ValueError, TypeError):
                precio_float = 0.0

            encontrado = False
            for item in self.carrito:
                if item['codigo'] == codigo or item['nombre'] == producto[0]:
                    item['cantidad'] += 1
                    encontrado = True
                    break
                    
            if not encontrado:
                item = {'codigo': codigo, 'nombre': producto[0], 'precio': precio_float, 'desc': producto[2], 'cantidad': 1}
                self.carrito.append(item)
            
            self.actualizar_lista_carrito()

            def reproducir_feedback(nombre_prod):
                import pygame
                import pyttsx3
                
                # Inicializar el mezclador de pygame de forma segura
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                
                # 1. Reproducir el MP3 del Pip a máximo volumen (1.0)
                try:
                    sonido_pip = pygame.mixer.Sound("sonidos/escanner_pi.mp3")
                    sonido_pip.set_volume(1.0)
                    sonido_pip.play()
                except Exception as e:
                    print(f"Error al cargar sonido mp3: {e}")
                
                # 2. Reproducir la voz con el nombre de la BD
                try:
                    motor = pyttsx3.init()
                    motor.setProperty('rate', 145) # Velocidad ligeramente ajustada para que suene más natural
                    motor.say(nombre_prod)
                    motor.runAndWait()
                except Exception as e:
                    print(f"Error con la voz: {e}")

            import threading
            hilo_audio = threading.Thread(target=reproducir_feedback, args=(producto[0],), daemon=True)
            hilo_audio.start()

            messagebox.showinfo("Escaneo Exitoso", f"El producto '{producto[0]}' ha sido escaneado e ingresado correctamente.")
        else:
            ruta_plantilla = f"imagenes/{codigo}.png"
            if not ruta_img_encontrada:
                img_temp = Image.new('RGB', (180, 150), color='#DDDDDD')
                img_temp.save(ruta_plantilla)
            
            self.lbl_imagen_actual.configure(image="", text="CÓDIGO NO\nREGISTRADO")
            messagebox.showwarning("Producto No Encontrado", f"El código {codigo} no está en la Base de Datos.\n\nSe ha creado la plantilla '{codigo}.png' en la carpeta de imágenes para que la reemplaces después.")
            
            self.registrar_nuevo_producto(codigo)

    def registrar_nuevo_producto(self, codigo):
        codigo = codigo.strip()
        if not codigo:
            messagebox.showinfo("Aviso", "Primero escanea o escribe un código para registrar.")
            return

        # Abrir ventana para registrar
        reg_win = tk.Toplevel(self.root)
        reg_win.title("Nuevo Producto")
        reg_win.geometry("400x350")
        reg_win.configure(bg=COLOR_FONDO)
        reg_win.transient(self.root)
        reg_win.grab_set()
        
        tk.Label(reg_win, text=f"Registrando\nCódigo: {codigo}", font=("Arial", 14, "bold"), bg=COLOR_FONDO, fg=COLOR_TOTAL).pack(pady=10)
        
        tk.Label(reg_win, text="Nombre:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=("Arial", 12)).pack()
        ent_nombre = tk.Entry(reg_win, font=("Arial", 12))
        ent_nombre.pack(pady=5)
        
        tk.Label(reg_win, text="Precio ($):", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=("Arial", 12)).pack()
        ent_precio = tk.Entry(reg_win, font=("Arial", 12))
        ent_precio.pack(pady=5)
        
        tk.Label(reg_win, text="Descripción:", bg=COLOR_FONDO, fg=COLOR_TEXTO, font=("Arial", 12)).pack()
        ent_desc = tk.Entry(reg_win, font=("Arial", 12))
        ent_desc.pack(pady=5)
        
        def guardar():
            try:
                nom = ent_nombre.get()
                pre = float(ent_precio.get())
                des = ent_desc.get()
                                
                self.cursor.execute("INSERT INTO productos (codigo_barras, nombre, precio, descripcion) VALUES (?,?,?,?)", (codigo, nom, pre, des))
                self.conexion.commit()
                messagebox.showinfo("Éxito", "Producto registrado.")
                reg_win.destroy()
                self.procesar_codigo(codigo)
            except Exception as e:
                print(f"Error detectado: {e}")
                messagebox.showerror("Error", "Datos inválidos. Verifica el precio o si ya existe.")
                
        tk.Button(reg_win, text="Guardar y Añadir", font=("Arial", 12, "bold"), bg=COLOR_TOTAL, command=guardar).pack(pady=20)

    def ver_base_datos(self):
        db_win = tk.Toplevel(self.root)
        db_win.title("Inventario - Base de Datos")
        db_win.geometry("650x400")
        db_win.configure(bg=COLOR_FONDO)
        db_win.transient(self.root)
        
        tk.Label(db_win, text="PRODUCTOS REGISTRADOS", font=("Arial", 16, "bold"), bg=COLOR_FONDO, fg=COLOR_TOTAL).pack(pady=10)
        
        # Crear tabla para visualizar la BD
        columnas = ("codigo", "nombre", "precio", "desc")
        tabla = ttk.Treeview(db_win, columns=columnas, show="headings")
        tabla.heading("codigo", text="Código")
        tabla.heading("nombre", text="Nombre")
        tabla.heading("precio", text="Precio")
        tabla.heading("desc", text="Descripción")
        
        tabla.column("codigo", width=120)
        tabla.column("nombre", width=180)
        tabla.column("precio", width=80)
        tabla.column("desc", width=220)
        
        tabla.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # CORRECCIÓN AQUÍ: Solicitar las columnas explícitamente para ignorar el ID de la base de datos
        self.cursor.execute("SELECT codigo_barras, nombre, precio, descripcion FROM productos")
        registros = self.cursor.fetchall()
        for fila in registros:
            # Ahora fila[2] garantiza ser la columna de precio
            try:
                precio_float = float(fila[2])
            except (ValueError, TypeError):
                precio_float = 0.0
                
            # fila[0]: codigo, fila[1]: nombre, fila[2]: precio_float, fila[3]: descripcion
            fila_formateada = (fila[0], fila[1], f"${precio_float:.2f}", fila[3])
            tabla.insert("", "end", values=fila_formateada)

    def actualizar_lista_carrito(self):
        for widget in self.frame_items.winfo_children():
            widget.destroy()
            
        subtotal = 0.0
        
        for idx, item in enumerate(self.carrito):
            cantidad = item.get('cantidad', 1)
            precio_unitario = item['precio']
            precio_total_item = precio_unitario * cantidad
            
            subtotal += precio_total_item
            
            bg_color = COLOR_ITEM_BG if idx % 2 == 0 else "#008B49"
            item_frame = tk.Frame(self.frame_items, bg=bg_color, pady=10)
            item_frame.pack(fill="x", pady=2)
            
            extensiones = ['.png', '.jpg', '.jpeg']
            ruta_img_encontrada = None
            for ext in extensiones:
                ruta_prueba = f"imagenes/{item['codigo']}{ext}"
                if os.path.exists(ruta_prueba):
                    ruta_img_encontrada = ruta_prueba
                    break
            
            if ruta_img_encontrada:
                img = Image.open(ruta_img_encontrada).resize((60, 60))
            else:
                img = Image.new('RGB', (60, 60), color='white') 
                
            img_tk = ImageTk.PhotoImage(img)
            lbl_img = tk.Label(item_frame, image=img_tk, bg="white")
            lbl_img.image = img_tk
            lbl_img.pack(side="left", padx=15)
            
            info_frame = tk.Frame(item_frame, bg=bg_color)
            info_frame.pack(side="left", fill="both", expand=True)
            
            # Mostramos el indicador (x2), (x3) si hay más de 1 artículo
            texto_nombre = f"{item['nombre']} (x{cantidad})" if cantidad > 1 else item['nombre']
            tk.Label(info_frame, text=texto_nombre, font=("Arial", 14, "bold"), bg=bg_color, fg=COLOR_TEXTO, anchor="w").pack(fill="x")
            
            # Subtítulo para mostrar el precio individual si está agrupado
            desc_text = item['desc']
            if cantidad > 1:
                desc_text += f" | Precio Unitario: ${precio_unitario:.2f}"
            tk.Label(info_frame, text=desc_text, font=("Arial", 10), bg=bg_color, fg="#DDDDDD", anchor="w").pack(fill="x")
            
            tk.Label(item_frame, text=f"${precio_total_item:.2f}", font=("Arial", 16, "bold"), bg=bg_color, fg=COLOR_TEXTO).pack(side="right", padx=20)
        
        iva = subtotal * 0.16
        total = subtotal + iva
        
        self.subtotal_actual = subtotal
        self.iva_actual = iva
        self.total_actual = total
        
        self.lbl_total.config(text=f"${total:.2f}")
    
    def mostrar_opciones_pago(self):
        if not self.carrito:
            messagebox.showwarning("Vacío", "No hay artículos en el carrito.")
            return
            
        pago_win = tk.Toplevel(self.root)
        pago_win.title("Método de Pago")
        pago_win.geometry("350x200")
        pago_win.configure(bg=COLOR_FONDO)
        pago_win.transient(self.root)
        pago_win.grab_set()
        
        tk.Label(pago_win, text=f"Total a cobrar: ${self.total_actual:.2f}", font=("Arial", 16, "bold"), bg=COLOR_FONDO, fg=COLOR_TOTAL).pack(pady=15)
        
        tk.Button(pago_win, text="💳 Pagar con Tarjeta", font=("Arial", 12, "bold"), bg="#005C9E", fg="white", command=lambda: self.pago_tarjeta(pago_win)).pack(fill="x", padx=40, pady=5)
        tk.Button(pago_win, text="💵 Pagar en Efectivo", font=("Arial", 12, "bold"), bg="#008B49", fg="white", command=lambda: self.pago_efectivo(pago_win)).pack(fill="x", padx=40, pady=10)

    def pago_tarjeta(self, parent_win):
        parent_win.destroy()
        tarjeta_win = tk.Toplevel(self.root)
        tarjeta_win.title("Terminal Bancaria - UX")
        tarjeta_win.geometry("400x380")
        tarjeta_win.configure(bg="#2b2b2b") # Color oscuro simulando terminal
        tarjeta_win.transient(self.root)
        tarjeta_win.grab_set()

        tk.Label(tarjeta_win, text="Terminal Punto de Venta", font=("Arial", 14, "bold"), bg="#2b2b2b", fg="white").pack(pady=15)

        # Selección de Banco de México
        tk.Label(tarjeta_win, text="Seleccione Banco:", bg="#2b2b2b", fg="white", font=("Arial", 11)).pack()
        bancos = ["BBVA", "Banamex", "Santander", "Banorte", "HSBC", "Scotiabank"]
        combo_banco = ttk.Combobox(tarjeta_win, values=bancos, state="readonly", font=("Arial", 11))
        combo_banco.current(0)
        combo_banco.pack(pady=5)

        # Número de tarjeta
        tk.Label(tarjeta_win, text="Número de Tarjeta (Débito/Crédito):", bg="#2b2b2b", fg="white", font=("Arial", 11)).pack(pady=(10,0))
        ent_tarjeta = tk.Entry(tarjeta_win, font=("Arial", 14), justify="center")
        ent_tarjeta.pack(pady=5)

        # PIN
        tk.Label(tarjeta_win, text="PIN (4 dígitos):", bg="#2b2b2b", fg="white", font=("Arial", 11)).pack(pady=(10,0))
        ent_nip = tk.Entry(tarjeta_win, font=("Arial", 14), show="*", justify="center")
        ent_nip.pack(pady=5)

        def aprobar():
            banco = combo_banco.get()
            if len(ent_tarjeta.get()) < 10 or not ent_nip.get():
                messagebox.showerror("Error", "Ingrese datos válidos de la tarjeta y el PIN.")
                return
            
            messagebox.showinfo("Transacción Aprobada", f"Pago procesado exitosamente por la red {banco}.")
            tarjeta_win.destroy()
            self.imprimir_ticket(metodo_pago=f"TARJETA {banco}")

        tk.Button(tarjeta_win, text="Aprobar Pago", bg="#008B49", fg="white", font=("Arial", 12, "bold"), command=aprobar).pack(pady=20)

    def pago_efectivo(self, parent_win):
        parent_win.destroy()
        efec_win = tk.Toplevel(self.root)
        efec_win.title("Cobro en Efectivo")
        efec_win.geometry("350x250")
        efec_win.configure(bg="#2b2b2b")
        efec_win.transient(self.root)
        efec_win.grab_set()

        tk.Label(efec_win, text=f"Total a Pagar: ${self.total_actual:.2f}", font=("Arial", 16, "bold"), bg="#2b2b2b", fg="#FFD700").pack(pady=15)

        tk.Label(efec_win, text="Efectivo recibido del cliente ($):", bg="#2b2b2b", fg="white", font=("Arial", 12)).pack()
        ent_recibido = tk.Entry(efec_win, font=("Arial", 16), justify="center")
        ent_recibido.pack(pady=10)
        ent_recibido.focus()

        def calcular_cobro():
            try:
                recibido = float(ent_recibido.get())
                if recibido < self.total_actual:
                    # Validar que no entregue menos dinero del que cuesta la cuenta
                    faltante = self.total_actual - recibido
                    messagebox.showerror("Efectivo Insuficiente", f"El cliente debe entregar al menos ${self.total_actual:.2f}\nFaltan ${faltante:.2f}")
                else:
                    # Calcular el cambio exacto
                    cambio = recibido - self.total_actual
                    if cambio > 0:
                        messagebox.showinfo("Cambio a entregar", f"Pago exitoso.\nDebe entregar al cliente un cambio de: ${cambio:.2f}")
                    else:
                        messagebox.showinfo("Cobro Exacto", "Pago exacto realizado. No se requiere dar cambio.")
                    
                    efec_win.destroy()
                    self.imprimir_ticket(metodo_pago="EFECTIVO", recibido=recibido, cambio=cambio)
            except ValueError:
                messagebox.showerror("Error", "Ingrese una cantidad numérica válida.")

        tk.Button(efec_win, text="Calcular y Cobrar", bg="#008B49", fg="white", font=("Arial", 12, "bold"), command=calcular_cobro).pack(pady=15)

    def pago_tarjeta(self, parent_win):
        parent_win.destroy()
        tarjeta_win = tk.Toplevel(self.root)
        tarjeta_win.title("Terminal Bancaria - UX")
        tarjeta_win.geometry("400x380")
        tarjeta_win.configure(bg="#2b2b2b") # Color oscuro simulando terminal
        tarjeta_win.transient(self.root)
        tarjeta_win.grab_set()

        tk.Label(tarjeta_win, text="Terminal Punto de Venta", font=("Arial", 14, "bold"), bg="#2b2b2b", fg="white").pack(pady=15)

        # Selección de Banco de México
        tk.Label(tarjeta_win, text="Seleccione Banco:", bg="#2b2b2b", fg="white", font=("Arial", 11)).pack()
        bancos = ["BBVA", "Banamex", "Santander", "Banorte", "HSBC", "Scotiabank"]
        combo_banco = ttk.Combobox(tarjeta_win, values=bancos, state="readonly", font=("Arial", 11))
        combo_banco.current(0)
        combo_banco.pack(pady=5)

        # Número de tarjeta
        tk.Label(tarjeta_win, text="Número de Tarjeta (Débito/Crédito):", bg="#2b2b2b", fg="white", font=("Arial", 11)).pack(pady=(10,0))
        ent_tarjeta = tk.Entry(tarjeta_win, font=("Arial", 14), justify="center")
        ent_tarjeta.pack(pady=5)

        # PIN
        tk.Label(tarjeta_win, text="PIN (4 dígitos):", bg="#2b2b2b", fg="white", font=("Arial", 11)).pack(pady=(10,0))
        ent_nip = tk.Entry(tarjeta_win, font=("Arial", 14), show="*", justify="center")
        ent_nip.pack(pady=5)

        def aprobar():
            banco = combo_banco.get()
            if len(ent_tarjeta.get()) < 10 or not ent_nip.get():
                messagebox.showerror("Error", "Ingrese datos válidos de la tarjeta y el PIN.")
                return
            
            messagebox.showinfo("Transacción Aprobada", f"Pago procesado exitosamente por la red {banco}.")
            tarjeta_win.destroy()
            self.imprimir_ticket(metodo_pago=f"TARJETA {banco}")

        tk.Button(tarjeta_win, text="Aprobar Pago", bg="#008B49", fg="white", font=("Arial", 12, "bold"), command=aprobar).pack(pady=20)

    def pago_efectivo(self, parent_win):
        parent_win.destroy()
        efec_win = tk.Toplevel(self.root)
        efec_win.title("Cobro en Efectivo")
        efec_win.geometry("350x250")
        efec_win.configure(bg="#2b2b2b")
        efec_win.transient(self.root)
        efec_win.grab_set()

        tk.Label(efec_win, text=f"Total a Pagar: ${self.total_actual:.2f}", font=("Arial", 16, "bold"), bg="#2b2b2b", fg="#FFD700").pack(pady=15)

        tk.Label(efec_win, text="Efectivo recibido del cliente ($):", bg="#2b2b2b", fg="white", font=("Arial", 12)).pack()
        ent_recibido = tk.Entry(efec_win, font=("Arial", 16), justify="center")
        ent_recibido.pack(pady=10)
        ent_recibido.focus()

        def calcular_cobro():
            try:
                recibido = float(ent_recibido.get())
                if recibido < self.total_actual:
                    # Validar que no entregue menos dinero del que cuesta la cuenta
                    faltante = self.total_actual - recibido
                    messagebox.showerror("Efectivo Insuficiente", f"El cliente debe entregar al menos ${self.total_actual:.2f}\nFaltan ${faltante:.2f}")
                else:
                    # Calcular el cambio exacto
                    cambio = recibido - self.total_actual
                    if cambio > 0:
                        messagebox.showinfo("Cambio a entregar", f"Pago exitoso.\nDebe entregar al cliente un cambio de: ${cambio:.2f}")
                    else:
                        messagebox.showinfo("Cobro Exacto", "Pago exacto realizado. No se requiere dar cambio.")
                    
                    efec_win.destroy()
                    self.imprimir_ticket(metodo_pago="EFECTIVO", recibido=recibido, cambio=cambio)
            except ValueError:
                messagebox.showerror("Error", "Ingrese una cantidad numérica válida.")

        tk.Button(efec_win, text="Calcular y Cobrar", bg="#008B49", fg="white", font=("Arial", 12, "bold"), command=calcular_cobro).pack(pady=15)

    def imprimir_ticket(self, metodo_pago, recibido=0.0, cambio=0.0):
        import threading

        def reproducir_sonido_impresora():
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            try:
                sonido_impresora = pygame.mixer.Sound("sonidos/print_ticket.mp3")
                sonido_impresora.set_volume(1.0)
                sonido_impresora.play()
            except Exception as e:
                print(f"Error al reproducir sonido de ticket: {e}")
                
        # Lanzar el sonido de la impresora
        threading.Thread(target=reproducir_sonido_impresora, daemon=True).start()

        import time, tempfile, webbrowser, os

        # Bloque HTML actualizado con meta charset y flex-start para escalabilidad infinita
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                /* align-items: flex-start evita que el ticket se corte cuando supera el alto de la pantalla */
                body {{ font-family: 'Courier New', Courier, monospace; background: #56B3C2; display: flex; justify-content: center; align-items: flex-start; padding: 40px 20px; min-height: 100vh; margin: 0; box-sizing: border-box; }}
                .ticket {{ background: white; width: 320px; height: max-content; padding: 20px 30px 40px 30px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); border-radius: 5px; }}
                .center {{ text-align: center; }}
                .bold {{ font-weight: bold; }}
                .line {{ border-top: 2px dashed #333; margin: 15px 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                td {{ padding: 4px 0; font-size: 14px; vertical-align: top; }}
                .right {{ text-align: right; }}
                .qty {{ width: 30px; font-weight: bold; }}
                .small-text {{ font-size: 11px; color: #666; display: block; }}
                h2 {{ margin: 0; font-size: 24px; }}
                .barcode {{ font-size: 35px; letter-spacing: 2px; text-align: center; margin-top: 20px; font-family: monospace; }}
            </style>
        </head>
        <body>
            <div class="ticket">
                <div class="center">
                    <h2>CASH RECEIPT</h2>
                    <br>
                    <p style="margin:2px;">SHOP: OXXO BUENAVISTA</p>
                    <p style="margin:2px;">DATE: {time.strftime("%d/%m/%Y %H:%M")}</p>
                </div>
                <div class="line"></div>
                <table>
        '''
        
        for item in self.carrito:
            cantidad = item.get('cantidad', 1)
            precio_unitario = item['precio']
            precio_total_item = precio_unitario * cantidad
            nombre = item['nombre'][:20]
            
            html += f"<tr><td class='qty'>{cantidad}x</td>"
            if cantidad > 1:
                html += f"<td>{nombre} <span class='small-text'>C/U: ${precio_unitario:.2f}</span></td>"
            else:
                html += f"<td>{nombre}</td>"
            html += f"<td class='right'>${precio_total_item:.2f}</td></tr>"
            
        html += f'''
                </table>
                <div class="line"></div>
                <table>
                    <tr><td>SUBTOTAL</td><td class='right'>${self.subtotal_actual:.2f}</td></tr>
                    <tr><td>TAX (16%)</td><td class='right'>${self.iva_actual:.2f}</td></tr>
                    <tr><td class="bold">TOTAL</td><td class='right bold'>${self.total_actual:.2f}</td></tr>
                </table>
                <div class="line"></div>
        '''
        
        # Lógica dinámica para mostrar información de efectivo o tarjeta
        if "TARJETA" in metodo_pago:
            html += f'<p style="margin-top: 15px; font-size: 14px;">Bank card: **** **** **** {metodo_pago}</p>'
        else:
            html += f'''
                <table>
                    <tr><td>PAGÓ CON:</td><td class='right'>${recibido:.2f}</td></tr>
                    <tr><td>CAMBIO:</td><td class='right'>${cambio:.2f}</td></tr>
                    <tr><td colspan="2" style="padding-top: 10px;">Método: EFECTIVO</td></tr>
                </table>
            '''

        html += '''
                <div class="line"></div>
                <h3 class="center">THANK YOU</h3>
                <div class="barcode">|| ||| || ||| | ||</div>
            </div>
        </body>
        </html>
        '''
        
        fd, path = tempfile.mkstemp(suffix='.html')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html)
            
        webbrowser.open('file://' + os.path.realpath(path))
        
        self.carrito = []
        self.actualizar_lista_carrito()
        messagebox.showinfo("Compra Finalizada", f"Pago completado con {metodo_pago}.")

    def cerrar(self):
        if hasattr(self, 'cap'):
            self.cap.release()
        self.conexion.close()
        self.root.destroy()

def iniciar_app():
    root = tk.Tk()
    app = CajaRegistradoraAPP(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar)
    root.mainloop()

if __name__ == "__main__":
    if not os.path.exists("imagenes"):
        os.makedirs("imagenes")
    # Iniciar con el Login
    root_login = tk.Tk()
    login = LoginWindow(root_login)
    root_login.mainloop()
