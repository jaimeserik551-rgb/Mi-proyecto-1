
import mysql.connector

def conectar():
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="escuela_nezagualtcoyot",
            port=3306
        )

        return conexion

    except mysql.connector.Error as error:
        print("Error al conectar:", error)
        return None


if __name__ == "__main__":
    conexion = conectar()

    if conexion:
        print("¡Conexión exitosa con MySQL!")
        conexion.close()
