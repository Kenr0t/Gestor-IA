import sqlite3
from Configuracion import RUTA_DB, LogTrad
from CorreoClient import Correo

db_log = LogTrad('dbLogger')


class DataBase:
    def __init__(self):
        RUTA_DB.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(RUTA_DB / "Datos.sqlite")
        with self.conn:
            self.conn.execute('''
            CREATE TABLE IF NOT EXISTS CORREOS (
                ID TEXT,
                ORIGEN TEXT,
                DESTINO TEXT,
                FECHA TEXT,
                ASUNTO TEXT,
                MENSAJE TEXT,
                CLASE TEXT
            );''')

    def execute_comit(self, sql, datos=None):
        try:
            with self.conn:  # Auto commit si sale bien, rollback en caso contrario
                if datos is None:
                    self.conn.execute(sql)
                else:
                    self.conn.execute(sql, datos)
        except Exception as e:
            db_log.error("Error BBDD", str(e))
            return False
        return True

    def add_correo(self, correo: Correo):
        datos = (correo.id, correo.origen, repr(correo.destino), correo.fecha, correo.asunto, correo.mensaje, correo.clase)
        if self.execute_comit('INSERT INTO CORREOS VALUES (?, ?, ?, ?, ?, ?, ?)', datos):
            db_log.debug('Correo con ID "{}" insertado con éxito.', correo.id)
        else:
            db_log.warning('No se ha insertado el correo con ID "{}".', correo.id)

    def update_correo(self, correo: Correo):
        if self.execute_comit('UPDATE CORREOS SET CLASE = ? WHERE ID = ?', (correo.clase, correo.id)):
            db_log.debug('Correo con ID "{}" actualizado con éxito.', correo.id)
        else:
            db_log.warning('No se ha actualizado el correo con ID "{}".', correo.id)

    def get_correos(self):
        curs = self.conn.cursor()
        datos = curs.execute('SELECT ID, ORIGEN, DESTINO, FECHA, ASUNTO, MENSAJE, CLASE FROM CORREOS').fetchall()
        curs.close()
        return [
            Correo(id, origen, eval(destino), asunto, mensaje, fecha, clase)
            for id, origen, destino, fecha, asunto, mensaje, clase in datos
        ]

    def exist(self, correo: Correo):
        sql = 'SELECT 1 FROM CORREOS WHERE ID = ?'
        curs = self.conn.cursor()
        datos = curs.execute(sql, (correo.id, )).fetchall()
        curs.close()
        return len(datos) > 0


if __name__ == '__main__':
    db = DataBase()

