import sqlite3

# 1. Crear o abrir el archivo de la base de datos
conexion = sqlite3.connect('caja_registradora.db')
cursor = conexion.cursor()

# 2. Crear la tabla de inventario si no existe
cursor.execute('''
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    precio REAL NOT NULL,
    descripcion TEXT NOT NULL
)
''')

# 3. Lista de productos para registrar (¡Cambia estos números por códigos reales de tu casa!)
productos_a_registrar = [
    ('724869007832', 'Gummy pop', 10.00, 'Dulce de gomita de 13g'),
    ('759686200098', 'Trabalenguas', 10.00, 'Paleta comestible de chile'),
    ('724869007870', 'Nugs', 10, 'Chocolate delicioso de nuez de 25g'),
    ('75003135', 'Boing', 20, 'Delicioso jugo de sabor de guayaba de 500ml'),
    ('7502208894779', 'Tribedoce', 45, 'Pastillas para la vitamina B de 100mg'),
    ('20801618', 'Crema para las manos', 80, 'Crema para umectarse las manos'),
    ('650240026768', 'Goicochea', 50, 'Jabon para lavarse el cabello con facilidad'),
    ('75076252', 'Desororante Universal', 70, 'Desororante para quitar los malos olores'),
    ('7503034937487', 'Cereal', 80, 'Rico cereal de sabon natural'),
    ('7501054526131', 'Beiersdorf', 50, 'Crema para humectarse las manos'),
    ('759684431050', 'Crema corporal', 75,'Crema para humectar la piel y piel cansada'),
    ('0759686200098', 'Trabalengua', 10.00, 'Paleta comestible de chile'),
    ('0724869007832', 'Gummy pop', 10, 'Dulce de gomita de 13g' ),
    ('0082200002206', 'Trabalenguas', 10.00, 'Paleta comestible de chile'),
    ('0650240026768', 'Goicoechea', 170.0, 'Crema para las piernas humectante'),
    ('4005900036711', 'Nivea men', 110.00, 'Desororante nivea para hombre black & whrite')
]

# 4. Insertar los productos en la tabla
for producto in productos_a_registrar:
    try:
        cursor.execute('''
            INSERT INTO productos (codigo_barras, nombre, precio, descripcion) 
            VALUES (?, ?, ?, ?)
        ''', producto)
    except sqlite3.IntegrityError:
        # Si el código de barras ya existe, este comando evita que el programa falle
        pass

# 5. Guardar los cambios y cerrar el archivo
conexion.commit()
conexion.close()

print("-> ¡Base de datos 'caja_registradora.db' creada y productos guardados!")
