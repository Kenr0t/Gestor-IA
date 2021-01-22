from time import time, sleep

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.exceptions import NotFittedError

from Configuracion import CLASES, LogTrad


gest_log = LogTrad('GestorLogger')


class GestorIA:
    nuevos_correos = []
    correos_con_clase = []
    correos_sin_clase = []
    ids_correos = set()

    def __init__(self, k_neighbors):
        self._tfid = TfidfVectorizer()
        # k_neighbors = round(math.sqrt(len(numero_mensajes_train)) / 2)
        self._knn_clf = KNeighborsClassifier(n_neighbors=k_neighbors)

    def add_correo(self, correo, es_nuevo=True):
        if correo.id not in self.ids_correos:
            self.ids_correos.add(correo.id)
            if correo.clase is None or correo.clase not in CLASES:
                self.correos_sin_clase.append(correo)
                es_nuevo = True
            else:
                self.correos_con_clase.append(correo)
            if es_nuevo:
                self.nuevos_correos.append(correo)

    def train(self):
        if len(self.correos_con_clase):
            t0 = time()
            mensajes, etiquetas = [], []
            gest_log.info(f'Entrenando KNN con {len(self.correos_con_clase)} correos...')
            for corr in self.correos_con_clase:
                mensajes.append(corr.mensaje)
                etiquetas.append(corr.clase)
            self._knn_clf.fit(self._tfid.fit_transform(mensajes), etiquetas)
            gest_log.info(f'Duración del entrenamiento: {time() - t0:.3f} segundos.')
        else:
            gest_log.info(f'No hay correos para entrear KNN por ahora...')

    def predecir(self):
        """
        Calcula la clase a la que podrían pertenecer los mensajes sin clasificar.
        :return:
        """
        mensajes = [c.mensaje for c in self.correos_sin_clase]
        try:
            predicciones = self._knn_clf.predict(self._tfid.transform(mensajes))
        except NotFittedError:
            gest_log.warning('Modelo no entrenado. No se realizarán predicciones para estos correos.')
            predicciones = [None] * len(self.correos_sin_clase)
        except ValueError:
            gest_log.warning('No hay suficientes ejemplos. No se realizarán predicciones para estos correos.')
            predicciones = [None] * len(self.correos_sin_clase)

        for corr, pred in zip(self.correos_sin_clase, predicciones):
            corr.mostrar(pred)

        for i, corr in reversed(list(enumerate(self.correos_sin_clase[:]))):  # Recorremos los que hemos dado como correctos
            # en orden contrario al introducido porque, al hacer pop, sacamos el elemento y el índice cambiaría.
            if corr.clase is not None:
                self.correos_con_clase.append(self.correos_sin_clase.pop(i))
