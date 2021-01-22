from tkinter import Tk, ttk, Button, INSERT, Text, StringVar
from CorreoClient import Correo, CorreoClient
from datetime import datetime
from time import time, sleep
from Gestor_IA import GestorIA
from DataBase import DataBase
import os


def ejecutar():
    cclient = CorreoClient()
    correos_db = DataBase()

    predictor = GestorIA(4)

    last_correo = datetime(1990, 1, 1)
    for corr in correos_db.get_correos():
        predictor.add_correo(corr, es_nuevo=False)

        if corr.fecha and corr.fecha > last_correo:
            last_correo = corr.fecha

    predictor.train()

    salir = False
    while not salir:
        try:
            for corr in cclient.sync_correo(last_correo):
                predictor.add_correo(corr, es_nuevo=True)

                if corr.fecha and corr.fecha > last_correo:
                    last_correo = corr.fecha
            print(f'\r{len(predictor.correos_sin_clase)} correos sin revisar a las {datetime.now():%H:%M:%S}', end='')
            sleep(30)
        except KeyboardInterrupt:
            print("""\n\nQué desea hacer:
                1.- Clasificar Correos
                
                0.- Salir""")
            selec = input('\nSelección: ')
            if selec == '0':
                salir = True
                print('Saliendo...')
            elif selec == '1':
                predictor.predecir()
        except Exception:
            print('Error inesperado... saliendo...')
            exit(1)

    if salir:  # Si se ha decidido salir, se guardarán los nuevos correos electrónicos
        for corr in predictor.nuevos_correos:
            if not correos_db.exist(corr):
                correos_db.add_correo(corr)
            else:
                correos_db.update_correo(corr)


if __name__ == '__main__':
    os.system('cls' if os.name == 'nt' else 'clear')  # Limpiamos la pantalla de la terminal
    ejecutar()
