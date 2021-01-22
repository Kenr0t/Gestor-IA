# Gestor IA

## Instalación 
- Descarga el proyecto en tu ordenador y descomprimirlo.
- Deberás tener correctamente instalado TKinter y Scikit Learn

## Manual de uso
Cuando tengamos todo instalado, nos posicionaremos con nuestra terminal dentro de nuestra carpeta Gestor IA descomprimida. Desde ahí debemos ejecutar el siguiente comando para arrancar la aplicacion:

``` sh
$ python __main__.py
```

La primera vez que ejecutemos nuestro gestor, deberemos congifurar el servidor IMAP y puerto del servicio de correo electrónico así como las credenciales del correo electrónico, probar la conexión, y en caso de poder conectarte correctamente, guardar dicha configuración haciendo click en el botón de Guardar.

Una vez validado el log-in, clickamos en guardar y cerramos la ventana. Se nos pedirá entonces seleccinar la carpeta que inspeccionará en busca de correos electrónicos. Es recomendable que en esta carpeta sólo esten los correos que se van a gestionar.
Cuando guardemos la selección del buzón y cerremos dicha ventana, veremos que en la terminal.

Llegados a este punto, la configuración estará guardada en el fichero *.config*, con la contraseña en base64 y todos los parámetros necesarios para iniciar sesión automáticamente, por lo que sólo será necesario hacerlo la primera vez.

En la ejecución normal del programa, se entrenará el modelo del gestor IA con todos los correos que ya tengamos clasificados y seguido a esto, revisará la carpeta de trabajo.
En el terminal nos quedará cuantos mensajes tenemos sin revisar en el buzón de trabajo y la fecha y hora de cuando se comprobó por última vez. 

Al presionar **Ctrl + C** se activará un menú para revisar el correo y poder asignarle una categoría o salir de la aplicación.

Si seleccionamos la opción de revisar los correos, comenzará a mostrarnos uno a uno, los correos pendientes, escrito en texto plano, con una lista desplegable, con la categoría predicha por el gestor, para dicho correo. En caso de ser correcto, click en guardar y aparecerá el siguiente correo.

Una vez terminados todos los correos, o cerrada la ventana, volveremos a la terminal con los correos que quedan por revisar (en el caso de que hubieran).

Si en vez de revisar el correo electrónico, presionamos salir, el programa guardará todos los datos actualizados en la base de datos de correos y se cerrará.