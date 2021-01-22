import pathlib
from configparser import ConfigParser
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import json


RUTA_PROYECTO = pathlib.Path(sys.path[0])

RUTA_DB = RUTA_PROYECTO / 'Data Bases'
RUTA_IDIOMAS = RUTA_PROYECTO / 'Idiomas'

CONFIG_FILE = RUTA_PROYECTO / '.config'
LOG_FILE = RUTA_PROYECTO / 'Logs/Clasificador.log'

CLASES = ['Anulacion', 'Nada', 'Pedido', 'Solicitud']

IDIOMA_CODIFICACION = 'es_ES'
IDIOMA = 'es_ES'

FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s] | %(name)s — %(message)s")


class Logger:
    def __init__(self, nombre):
        # Crea un Handler para mostrar en la consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(FORMATTER)
        # Crea un handler para escribir en ficheros que van rotando los lunes de cada semana
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(LOG_FILE, when='W6')
        file_handler.setFormatter(FORMATTER)

        self.logger = logging.Logger(nombre)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def error(self, mensaje, *args, **kwargs):
        if args or kwargs:
            mensaje = mensaje.format(*args, **kwargs)
        self.logger.error(msg=mensaje)

    def warning(self, mensaje, *args, **kwargs):
        if args or kwargs:
            mensaje = mensaje.format(*args, **kwargs)
        self.logger.warning(msg=mensaje)

    def info(self, mensaje, *args, **kwargs):
        if args or kwargs:
            mensaje = mensaje.format(*args, **kwargs)
        self.logger.info(msg=mensaje)

    def debug(self, mensaje, *args, **kwargs):
        if args or kwargs:
            mensaje = mensaje.format(*args, **kwargs)
        self.logger.debug(msg=mensaje)


config_logger = Logger('ConfigLogger')


class Traductor:
    frases = {}
    idioma = None

    def __init__(self, idioma=IDIOMA_CODIFICACION):
        """
        Inicializa el traductor, si es Español, sobreescribe el método traduce por uno que devuelve la entrada
        :param idioma:
        """
        self.idioma = idioma
        if self.idioma == 'es_ES':
            self.traduce = lambda x: x
        else:
            try:
                with open(RUTA_IDIOMAS / f'{self.idioma}.json') as f:
                    self.frases = json.load(f)
            except FileNotFoundError:
                print(f'Traducción no encontrada, generando un nuevo fichero de traducción para {self.idioma}')
            except Exception as e:
                print(f'Error desconocido: {e}')

    def traduce(self, frase):
        """
        Devuelve la traducción de la frase pasada por parámetro si existe traducción.
        En caso contrario, devuelve la original y la apunta como pendiente de traducir
        :param frase: frase a traducir.
        :return: frase traducida.
        """
        if frase in self.frases and self.frases[frase] is not None:
            frase_trad = self.frases[frase]
        else:
            if frase not in self.frases:
                self.frases[frase] = None
                self.guardar()
                config_logger.warning('Frase no traducida, se ha añadido al diccionario. Se muestra la frase original.')
            else:
                config_logger.warning('Frase pendiente de traducir.')
            frase_trad = frase
        return frase_trad

    def guardar(self):
        """
        Persiste las nuevas frases en un fichero json
        """
        if self.idioma != IDIOMA_CODIFICACION:
            with open(RUTA_IDIOMAS / f'{self.idioma}.json', 'w') as f:
                json.dump(self.frases, f, indent=4)

    def get_no_traducidas(self):
        return [k for k, v in self.frases.items() if v is None]


class LogTrad(Logger, Traductor):
    def __init__(self, nombre):
        Logger.__init__(self, nombre)
        Traductor.__init__(self, IDIOMA)

    def error(self, mensaje, *args, **kwargs):
        Logger.error(self, self.traduce(mensaje), *args, **kwargs)

    def warning(self, mensaje, *args, **kwargs):
        Logger.warning(self, self.traduce(mensaje), *args, **kwargs)

    def info(self, mensaje, *args, **kwargs):
        Logger.info(self, self.traduce(mensaje), *args, **kwargs)

    def debug(self, mensaje, *args, **kwargs):
        Logger.debug(self, self.traduce(mensaje), *args, **kwargs)
