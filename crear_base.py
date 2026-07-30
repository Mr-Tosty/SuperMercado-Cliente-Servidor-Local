import sqlite3

conexion = sqlite3.connect('caja_registradora.db')
cursor = conexion.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    precio REAL NOT NULL,
    descripcion TEXT NOT NULL
)
''')

# 3. Lista de productos para registrar
productos_a_registrar = [
    #codigo de barras nombre        precio  descripcion
    ('XXXXXXXXXXXX', 'abcdefghijkl', 00.00, 'abcdefghijklmnopqrstuvwxyz'),
    ('XXXXXXXXXXXX', 'abcdefghijkl', 00.00, 'abcdefghijklmnopqrstuvwxyz')
]

for producto in productos_a_registrar:
    try:
        cursor.execute('''
            INSERT INTO productos (codigo_barras, nombre, precio, descripcion) 
            VALUES (?, ?, ?, ?)
        ''', producto)
    except sqlite3.IntegrityError:
        pass

conexion.commit()
conexion.close()

print("-> ¡Base de datos 'caja_registradora.db' creada y productos guardados!")
