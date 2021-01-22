import imaplib
import os
from imaplib import IMAP4
import email
from email.header import decode_header
from email.parser import BytesFeedParser
import re, json
from base64 import b64encode, b64decode
from configparser import ConfigParser
from socket import gaierror
from datetime import datetime
from tkinter import Tk, ttk, Button, INSERT, Text, StringVar


from Configuracion import CONFIG_FILE, CLASES, LogTrad


es_correo = re.compile(r'[\w\.\-]+@[\w-]+\.[\w]+')
get_buzon = re.compile('^\(.*\) ".*" "(.*)"$')

mail_log = LogTrad('MailLogger')

trad = mail_log.traduce


class ConnError(Exception):
    pass


class BuzonError(Exception):
    pass


class Correo:
    id = None
    origen = None
    destino = None
    fecha = None
    asunto = None
    mensaje = None
    clase = None

    def __init__(self, id, origen, destino, asunto, mensaje, fecha=None, clase=None):
        self.id = id
        self.origen = origen
        if isinstance(destino, str):
            destino = [d.strip() for d in destino.split(',')]
        self.destino = destino
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
                # fecha = datetime.strptime(fecha, '%d/%m/%Y %H:%M:%S')
            except ValueError:
                mail_log.warning(f'No se reconoce fecha en "{fecha}"')
                fecha = None
            except Exception as e:
                mail_log.error(e)
                fecha = None
        self.fecha = fecha
        self.asunto = asunto
        self.mensaje = mensaje
        self.clase = clase

    @classmethod
    def set_traductor(cls, traductor):
        cls.traductor = traductor

    @classmethod
    def from_bytes(cls, corre_b):
        mail_parser = BytesFeedParser()
        mail_parser.feed(corre_b)
        correo = mail_parser.close()
        txt_codec = correo.get_content_charset()
        transfer_codec = correo['Content-Transfer-Encoding']

        origen, codec = decode_header(correo['from'])[0]
        origen = origen.decode(codec)

        destino = es_correo.findall(' '.join([correo.get('Cc', ''), correo.get('To', '')]))
        message_id = correo['Message-Id']
        fecha = datetime.strptime(correo['date'], '%a, %d %b %Y %H:%M:%S %z')
        fecha = datetime(fecha.year, fecha.month, fecha.day, fecha.hour, fecha.minute, fecha.second)

        if transfer_codec is None:
            asunto = correo['subject']
            payload = correo.get_payload(0)
            transfer_codec = payload['Content-Transfer-Encoding']
            txt_codec = payload.get_content_charset()
            mensaje = payload.get_payload(decode=transfer_codec).decode(txt_codec)
        elif transfer_codec == '7bit':
            asunto, codec = decode_header(correo['subject'])[0]
            asunto = asunto.decode(codec)
            mensaje = correo.get_payload()
        elif transfer_codec == 'quoted-printable':
            asunto = correo['subject']
            mensaje = correo.get_payload(decode=transfer_codec).decode(txt_codec)
        else:
            raise NotImplementedError(mail_log.error('Este transfer_codec no está implememntado: {}', transfer_codec))

        return cls(message_id, origen, destino, asunto, mensaje, fecha)

    def mostrar(self, predic=None):
        root = Tk()
        mensaje = Text(root)
        correo_txt = '\n'.join([
            f'{trad("Para")}: {", ".join(self.destino)}',
            f'{trad("Fecha")}: {self.fecha:%d/%m/%Y %H:%M:%S}',
            f'{trad("Asunto")}: {self.asunto}',
            f'{trad("Mensaje")}:\n{self.mensaje}'
        ])
        mensaje.insert(INSERT, correo_txt)
        mensaje.pack()
        clase = StringVar()
        clase_cb = ttk.Combobox(root, textvariable=clase, state='readonly', values=CLASES)
        if predic is not None:
            if predic not in CLASES:
                raise ValueError(f'La preducción de clase "{predic}" no es válida.')
            clase_cb.set(predic)
        else:
            if self.clase is not None and self.clase not in CLASES:
                mail_log.warning(f'La clase "{self.clase}" no era correcta')
                self.clase = None
            if self.clase is None:
                clase_cb.set(CLASES[0])
            else:
                clase_cb.set(self.clase)

        clase_cb.pack()

        def guardar():
            root.destroy()
            self.clase = clase.get()

        guardar_bt = Button(root, text='Guardar', command=guardar)
        guardar_bt.pack()
        root.mainloop()

    def __repr__(self):
        return json.dumps(self.dict(), indent=4)

    def dict(self):
        return {
            'id': self.id,
            'origen': self.origen,
            'destino': self.destino,
            'fecha': self.fecha.strftime('%Y-%m-%d %H:%M:%S'),
            'asunto': self.asunto,
            'mensaje': self.mensaje,
            'clase': self.clase
        }


class CorreoClient:
    host_servidor = None
    _port_servidor = None
    _email = None
    _passwd = None
    email_cli = None
    buzon = None

    def __init__(self):
        try:
            self.import_config()
        except FileNotFoundError:
            self.login_menu()
        except Exception as e:
            mail_log.error('Error desconocido al intentar cargar el fichero...')
            mail_log.warning('Borrando el fichero corrupto...')
            os.remove(CONFIG_FILE)
            self.login_menu()
        else:
            try:
                self.conectar()
            except Exception as e:
                mail_log.error('Error: {}', e.args[0])
                self.login_menu()

        # A partir de este punto debe haber una conexión activa
        if not self.email_cli:
            raise ConnError('No se puede continuar sin una conexión...')
        mail_log.info('Conectado como {}', self.email)
        if not self.buzon:
            self.seleccionar_buzon()
        status, _ = self.email_cli.select(self.buzon)
        if status == 'OK':
            mail_log.info('En el buzon {}', self.buzon)
        else:
            raise BuzonError('Error desconocido al seleccionar el buzón ' + self.buzon)

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, new_corr):
        if es_correo.match(new_corr):
            self._email = new_corr
        else:
            raise ValueError(trad('Formato de correo electrónico incorrecto.'))

    @property
    def passwd(self):
        if self._passwd is None:
            return None
        else:
            return b64decode(self._passwd).decode('UTF-8')

    @passwd.setter
    def passwd(self, new_passwd):
        self._passwd = b64encode(new_passwd.encode('UTF-8'))

    @property
    def port_servidor(self):
        return self._port_servidor

    @port_servidor.setter
    def port_servidor(self, new_port):
        new_port = new_port.strip()
        if new_port is None:
            self._port_servidor = None
        elif new_port.isnumeric():
            self._port_servidor = new_port
        else:
            raise ValueError('El valor del puerto debe ser un númmero.')

    def conectar(self):
        try:
            if self.port_servidor:
                self.email_cli = imaplib.IMAP4_SSL(self.host_servidor, port=self.port_servidor)
            else:
                self.email_cli = imaplib.IMAP4_SSL(self.host_servidor)
            self.email_cli.login(self.email, self.passwd)
        except gaierror as cr:
            if cr.errno == 8:
                raise ValueError('El servidor indicado no responde o no existe')
            else:
                raise
        except IMAP4.error as err:
            print(err)
            raise ValueError(f'Usuario o contraseña incorrecto...')

    def login_menu(self):
        from tkinter import Tk, Entry, Label, Frame, Button, END, messagebox
        root = Tk()
        root.title = 'Log In'

        frame_login = Frame(root)
        frame_login.pack()
        host_var = Entry(frame_login)
        if self.host_servidor:
            host_var.insert(0, self.host_servidor)
        port_var = Entry(frame_login)
        if self.port_servidor:
            port_var.insert(0, self.port_servidor)
        user_var = Entry(frame_login)
        if self.email:
            user_var.insert(0, self.email)
        pass_var = Entry(frame_login, show='*')
        if self.passwd:
            pass_var.insert(0, self.passwd)

        campos = [
            (trad('Host Servidor'), host_var), (trad('Puerto'), port_var),
            (trad('Correo'), user_var), (trad('Contraseña'), pass_var)
        ]
        for linea, (nombre, var) in enumerate(campos):
            var_label = Label(frame_login, text=f'{nombre}:')
            var.grid(row=linea, column=1, padx=5, pady=5)
            var_label.grid(row=linea, column=0, padx=5, pady=5)

        frame_botones = Frame(root)
        frame_botones.pack()

        def guardar():
            self.export_config()
            messagebox.showinfo(trad('Guardado!'), trad('Configuración guardada correctamente'))

        def borrar():
            for campo, var in campos:
                var.delete(0, END)

        bt_guardar = Button(frame_botones, text=trad('Guardar'), command=guardar, state='disabled')
        bt_guardar.grid(row=0, column=0, padx=10, pady=10)

        def probar_conn():
            bt_guardar.config(state='disabled')
            try:
                self.host_servidor = host_var.get()
                if port_var.get():
                    self.port_servidor = port_var.get()
                self.email = user_var.get()
                self.passwd = pass_var.get()
                self.conectar()
            except ValueError as ve:
                messagebox.showerror('Error en la entrada', ve.args[0])
            except Exception as e:
                messagebox.showerror('Ooops...', e)
                raise
            else:
                messagebox.showinfo(trad('Conectado!'), trad('Conectado correctamente al servidor de correos.'))
                bt_guardar.config(state='normal')

        Button(frame_botones, text=trad('Conectar'), command=probar_conn).grid(row=0, column=1, padx=10, pady=10)
        Button(frame_botones, text=trad('Borrar'), command=borrar).grid(row=0, column=2, padx=10, pady=10)

        root.mainloop()

    def export_config(self):
        if not all([self.host_servidor, self._email, self._passwd]):
            raise AttributeError('Para exportar la configuración, todos los campos deben estar rellenos.')

        config = ConfigParser()
        config.add_section('MAIL')
        config['MAIL']['host'] = self.host_servidor
        if self.port_servidor is not None:
            config['MAIL']['port'] = self.port_servidor
        config['MAIL']['user'] = self._email
        config['MAIL']['pass'] = self._passwd.decode('UTF-8')

        if self.buzon:
            config.add_section('BUZON')
            config['BUZON']['path'] = self.buzon

        with open(CONFIG_FILE, 'w') as cf:
            config.write(cf)

    def import_config(self):
        config = ConfigParser()
        try:
            with open(CONFIG_FILE, 'r') as cf:
                config.read_file(cf)
        except Exception:
            raise FileNotFoundError
        else:
            assert 'MAIL' in config, 'No se encuentran datos del correo electrónico en el fichero de configuración.'
            self.host_servidor = config['MAIL']['host']
            if 'port' in config['MAIL']:
                self.port_servidor = config['MAIL']['port']
            self._email = config['MAIL']['user']
            self._passwd = config['MAIL']['pass'].encode('UTF-8')

            if 'BUZON' in config:
                self.buzon = config['BUZON']['path']

    def seleccionar_buzon(self):
        from tkinter import Tk, ttk, StringVar, Entry, Label, Frame, Button, END, messagebox
        root = Tk()
        root.title = trad('Seleccionar Buzon')
        # Obtengo el listado de buzones
        status, buzones = self.email_cli.list()
        if status == 'OK':
            buzones = [get_buzon.match(b.decode('UTF8')).groups()[0] for b in buzones]
            buzon = StringVar()
            campo_buz = ttk.Combobox(root, state='readonly', textvariable=buzon, values=buzones)
            buzom_lb = Label(root, text=trad('Buzon:'))
            campo_buz.grid(row=0, column=1, padx=10, pady=10)
            buzom_lb.grid(row=0, column=0, padx=10, pady=10)
            Button(root, text=trad('Guardar'), command=root.destroy).grid(row=0, column=0, padx=10, pady=10)
        else:
            raise ConnError('Error al recuperar los buzones...')
        root.mainloop()
        self.buzon = buzon.get()
        status, _ = self.email_cli.select()
        assert status == 'OK', 'Error desconocido al seleccionar el buzón ' + self.buzon
        self.export_config()

    def sync_correo(self, fecha_desde=None):
        self.email_cli.check()
        if fecha_desde is None:
            estado_busqueda, indices_mensajes = self.email_cli.search(None, 'ALL')
        else:
            estado_busqueda, indices_mensajes = self.email_cli.search(None, f'(SINCE "{fecha_desde:%d-%b-%Y}")')
        assert estado_busqueda == 'OK', 'Fallo al encontrar los mensajes de la bandeja de entrada...'
        correos = []
        for num in indices_mensajes[0].split():
            estado_mensaje, respuesta_serv = self.email_cli.fetch(num, '(RFC822)')
            assert estado_mensaje == 'OK', 'Fallo al encontrar los mensajes de la bandeja de entrada...'
            for linea in respuesta_serv:
                if isinstance(linea, tuple):
                    _, bytes_correo = linea
                    correos.append(Correo.from_bytes(bytes_correo))
        return correos


def main():
    cclient = CorreoClient()
    correos = cclient.sync_correo(datetime(2020, 5, 23))
    for corr in correos:
        print(corr.id)


if __name__ == '__main__':
    main()
