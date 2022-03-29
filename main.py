import numpy as np
from dotmap import DotMap
from flask import Flask, render_template
import sqlite3
import json
import pandas as pd
import plotly.express as px

app = Flask(__name__)


###### CREACIÓN DE TABLAS PARA LA BASE DE DATOS ######
@app.route('/')
def hello():
    con = sqlite3.connect("example2.db", timeout=10)
    con.execute("PRAGMA foreign_keys = 1")
    cur = con.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS legal(url text primary key, cookies boolean, aviso boolean, proteccion_de_datos '
        'boolean, creacion number)')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users(name text primary key, telefono text, contrasena text, provincia text, '
        'permisos boolean)')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS emails(name text, total number, phising number, clicados number, foreign key ('
        'name) references users (name))')
    cur.execute('CREATE TABLE IF NOT EXISTS ips(name text, ip text, fecha text , foreign key (name) references users ('
                'name))')

    con.commit()
    cur.close()
    return "<p>Hello World! Accede a /dataframe para ver los datos y gráficos.</p>"


# ------------- EJERCICIO 2 -------------
###### LECTURA DE DATOS JSON PARA LA INICIALIZACIÓN DE LA BASE DE DATOS ######
@app.route('/func')
def func():
    con = sqlite3.connect("example2.db", timeout=10)
    con.execute("PRAGMA foreign_keys = 1")
    cur = con.cursor()

    # Carga de datos del fichero Legal.json
    f = open("data/legal.json")
    data = json.load(f)
    # print(data)
    for entry in data["legal"]:
        url = list(entry.keys())[0]
        cookies = int(entry[url]["cookies"])
        aviso = int(entry[url]["aviso"])
        proteccion_de_datos = int(entry[url]["proteccion_de_datos"])
        creacion = entry[url]["creacion"]
        cur.execute(
            'INSERT INTO legal VALUES("{}", "{}", "{}", "{}", "{}")'.format(url, cookies, aviso, proteccion_de_datos,
                                                                            creacion))
        # print("name: {}\nCookies: {}\nAviso: {}\nProteccion de Datos: {}\ncreacion: {}\n".format(url, cookies, aviso,
        #                                                                                          proteccion_de_datos,
        #                                                                                          creacion))
    f.close()

    # Carga de datos del fichero Users.json
    f = open("data/users.json")
    data = json.load(f)
    # print(data)
    for entry in data["usuarios"]:
        name = list(entry.keys())[0]
        telefono = entry[name]["telefono"]
        contrasena = entry[name]["contrasena"]
        provincia = entry[name]["provincia"]
        permisos = entry[name]["permisos"] == "1"
        emails = entry[name]["emails"]
        fechas = entry[name]["fechas"]
        ips = entry[name]["ips"]
        # Comprobación de valores coherentes y no nulos
        cur.execute('INSERT INTO users VALUES("{}", "{}", "{}", "{}", "{}")'
                    .format(name, telefono, contrasena, provincia, permisos))
        cur.execute('INSERT INTO emails values("{}", "{}", "{}", "{}")'
                    .format(name, emails["total"], emails["phishing"], emails["clicados"]))
        if len(ips) == len(fechas) and len(fechas) > 0 and ips is not None:
            for i in range(len(fechas)):
                cur.execute('INSERT INTO ips values("{}", "{}", "{}")'
                            .format(name, ips[i], fechas[i]))
                pass
        else:
            for i in range(len(fechas)):
                cur.execute('INSERT INTO ips values("{}", "{}", "{}")'
                            .format(name, None, fechas[i]))
                pass
        # print( "Name: {}\nTelefono: {}\nContrasena: {}\nProvincia: {}\nPermisos: {}\nEmails: {}\nFechas: {}\nIps: {
        # }\n".format( name, telefono, contrasena, provincia, permisos, emails, fechas, ips))
        pass
    con.commit()
    cur.close()
    return "<h1>Base de datos inicializada correctamente</h1>"


# ------------- EJERCICIOS 2, 3 Y 4 -------------
@app.route('/dataframe')
def dataframe():
    con = sqlite3.connect("example2.db", timeout=10)
    # ------------- EJERCICIO 2 -------------
    # Inicializamos Dataframe "datafreim" con los datos no nulos y coherentes
    query = pd.read_sql_query(
        'SELECT u.*, i.ip, i.fecha, e.total, e.phising, e.clicados FROM users u JOIN ips i ON u.name=i.name '
        'JOIN emails e ON u.name=e.name WHERE u.provincia != "None" AND '
        'u.telefono != "None" AND i.ip LIKE "%.%.%.%"', con, "name")
    datafreim = pd.DataFrame(query,
                             columns=["name", "telefono", "contrasena", "provincia", "permisos", "ip", "fecha", "total",
                                      "phising", "clicados"])

    datafreim = datafreim.drop("name", axis=1)
    # print(datafreim)

    # Dataframe "original" con una fila por usuario, con los datos bidimensionales (IPs, Fechas) cargados como arrays
    original = datafreim.groupby(["name"], dropna=False).agg(
        {"fecha": np.array, "ip": np.array, "telefono": "first", "contrasena": "first", "provincia": "first",
         "permisos": "first", "total": "first", "phising": "first", "clicados": "first"})

    # Agrupaciones
    fecha = datafreim.groupby(["name"], dropna=True).agg({"fecha": "count"})
    ips = datafreim.groupby(["name"], dropna=True).agg({"ip": "count"})
    emails = datafreim.groupby(["name"], dropna=True).agg({"total": "first"})

    # Cálculos para fechas de inicio de sesión
    mediafecha = fecha.mean()["fecha"]
    desviacionfecha = fecha.std()["fecha"]
    # Cálculos para el número de IPs
    mediaips = ips.mean()["ip"]
    desviacionips = ips.std()["ip"]
    # Cálculos para el número de emails
    mediaemails = emails.mean()["total"]
    desviacionemails = emails.std()["total"]
    # Nº total de usuarios (muestras)
    usuarios = original.shape[0]
    # Máximos y mínimos de fechas/emails
    maxfecha = fecha.max()["fecha"]
    minfecha = fecha.min()["fecha"]
    maxemails = emails.max()["total"]
    minemails = emails.min()["total"]

    # DotMap para representación organizada en web
    ejer2 = {
        "mediafecha": round(mediafecha, 2),
        "desviacionfecha": round(desviacionfecha, 2),
        "mediaips": round(mediaips, 2),
        "desviacionips": round(desviacionips, 2),
        "mediaemails": round(mediaemails, 2),
        "desviacionemails": round(desviacionemails, 2),
        "usuarios": usuarios,
        "maxfecha": maxfecha,
        "minfecha": minfecha,
        "maxemails": maxemails,
        "minemails": minemails
    }
    ejer2 = DotMap(ejer2)

    # ------------- EJERCICIO 3 -------------
    # Creamos las 4 agrupaciones
    usuariosperm = original.loc[original.permisos == "False", ['total', 'phising', 'clicados']]
    adminperm = original.loc[original.permisos == "True", ['total', 'phising', 'clicados']]
    mayor200 = original.loc[original.total >= 200, ['total', 'phising', 'clicados']]
    menor200 = original.loc[original.total < 200, ['total', 'phising', 'clicados']]

    # print(usuariosperm)
    # print(adminperm)
    # print(mayor200)
    # print(menor200)

    # Cálculos para usuarios
    usuariosperm_num = usuariosperm.shape[0]
    usuariosperm_mediana = usuariosperm.median()["phising"]
    usuariosperm_media = usuariosperm.mean()["phising"]
    usuariosperm_varianza = usuariosperm.var()["phising"]
    usuariosperm_max = usuariosperm.max()["phising"]
    usuariosperm_min = usuariosperm.min()["phising"]

    # Cálculos para administradores
    adminperm_num = adminperm.shape[0]
    adminperm_mediana = adminperm.median()["phising"]
    adminperm_media = adminperm.mean()["phising"]
    adminperm_varianza = adminperm.var()["phising"]
    adminperm_max = adminperm.max()["phising"]
    adminperm_min = adminperm.min()["phising"]

    # Cálculos para usuarios que hayan recibido más de 200 correos
    mayor200f_num = mayor200.shape[0]
    mayor200f_mediana = mayor200.median()["phising"]
    mayor200f_media = mayor200.mean()["phising"]
    mayor200f_varianza = mayor200.var()["phising"]
    mayor200f_max = mayor200.max()["phising"]
    mayor200f_min = mayor200.min()["phising"]

    # Cálculos para usuarios que hayan recibido menos de 200 correos
    menor200f_num = menor200.shape[0]
    menor200f_mediana = menor200.median()["phising"]
    menor200f_media = menor200.mean()["phising"]
    menor200f_varianza = menor200.var()["phising"]
    menor200f_max = menor200.max()["phising"]
    menor200f_min = menor200.min()["phising"]

    # DotMap para representación organizada en web
    # Tomamos como premisa que no existen valores ausentes, ya que han sido eliminados durante la creación del Dataframe
    ejer3 = {
        "usuario_observaciones": usuariosperm_num,
        "usuario_ausentes": 0,
        "usuario_mediana": round(usuariosperm_mediana, 2),
        "usuario_media": round(usuariosperm_media, 2),
        "usuario_varianza": round(usuariosperm_varianza, 2),
        "usuario_max": usuariosperm_max,
        "usuario_min": usuariosperm_min,
        "admin_observaciones": adminperm_num,
        "admin_ausentes": 0,
        "admin_mediana": round(adminperm_mediana, 2),
        "admin_media": round(adminperm_media, 2),
        "admin_varianza": round(adminperm_varianza, 2),
        "admin_max": adminperm_max,
        "admin_min": adminperm_min,
        "mayor200_observaciones": round(mayor200f_num, 2),
        "mayor200_ausentes": 0,
        "mayor200_mediana": round(mayor200f_mediana, 2),
        "mayor200_media": round(mayor200f_media, 2),
        "mayor200_varianza": round(mayor200f_varianza, 2),
        "mayor200_max": mayor200f_max,
        "mayor200_min": mayor200f_min,
        "menor200_observaciones": menor200f_num,
        "menor200_ausentes": 0,
        "menor200_mediana": round(menor200f_mediana, 2),
        "menor200_media": round(menor200f_media, 2),
        "menor200_varianza": round(menor200f_varianza, 2),
        "menor200_max": menor200f_max,
        "menor200_min": menor200f_min
    }
    ejer3 = DotMap(ejer3)

    # ------------- EJERCICIO 4 -------------

    # Dataframe datos de legal
    query_legal = pd.read_sql_query('SELECT url, cookies, aviso, proteccion_de_datos, creacion FROM legal', con)
    datafreim_legal = pd.DataFrame(query_legal, columns=["url", "cookies", "aviso", "proteccion_de_datos", "creacion"])
    # print(datafreim_legal)

    # ----- 4.2 PAGINAS WEB CON POLITICAS DESACTUALIZADAS -------
    datafreim_legal["inseguro"] = datafreim_legal["cookies"] + datafreim_legal["aviso"] + datafreim_legal[
        "proteccion_de_datos"]
    datafreim_legal = datafreim_legal.dropna(axis=1)
    datafreim_legal.sort_values(by=["inseguro"], ascending=True, inplace=True)
    paginas_inseguras = datafreim_legal.head(5)
    # print(paginas_inseguras)
    grafico_paginas = px.bar(paginas_inseguras, x="url", y=["cookies", "aviso", "proteccion_de_datos"],
                             title="Páginas con políticas desactualizadas")
    grafico_paginas.show()

    # ----- 4.4 MOSTRAR SEGÚN AÑO LAS WEBS QUE CUMPLEN POLITICA PRIVACIDAD VS LAS QUE NO LA CUMPLEN -------
    politicas = datafreim_legal
    # Si son inseguros = 1, si son seguros = 0
    politicas["inseguro"] = (politicas["inseguro"] < 3) * 1
    politicas["seguro"] = (politicas["inseguro"] == 0) * 1
    # print(politicas)
    politicas = politicas.drop(columns=["cookies", "aviso", "proteccion_de_datos"])
    politicas = politicas.groupby(["creacion"]).agg(
        {"inseguro": "sum", "seguro": "sum", "url": "first", "creacion": "first"})
    # print(politicas)

    fig = px.line(politicas, x="creacion", y="inseguro", title="Nº de webs inseguras")
    fig.show()
    fig = px.line(politicas, x="creacion", y="seguro", title="Nº de webs seguras")
    fig.show()

    # SEPARAMOS POR CONTRASEÑAS VULNERADAS
    # Diccionario con los hashes comprometidos de los usuarios
    diccionario = open("data/diccionario.txt", "r")
    dict_hashes = diccionario.read().split("\n")
    diccionario.close()

    datafreim_userpass = original
    # print(datafreim_userpass)
    datafreim_userpass["segura"] = (datafreim_userpass["contrasena"].isin(dict_hashes)) * 1
    # print(datafreim_userpass)

    # Dataframes de usuarios comprometidos  / no comprometidos
    comprometidos = datafreim_userpass[datafreim_userpass.segura == 1]
    nocomprometidos = datafreim_userpass[datafreim_userpass.segura == 0]

    # ----- 4.1 10 USUARIOS MÁS CRÍTICOS -----
    comprometidos["prob-clic"] = comprometidos["clicados"] / comprometidos["phising"]
    criticos = comprometidos
    criticos.sort_values(by=["prob-clic"], ascending=False, inplace=True)
    criticos = criticos.head(10)
    # print(criticos)
    fig = px.bar(criticos, x=criticos.index, y='prob-clic', title="Top 10 usuarios más críticos")
    fig.show()

    # ----- 4.3 MEDIA DE CONEXIONES CON CONTRASEÑA VULNERABLE VS NO VULNERABLE -----
    conexionesvuln = datafreim_userpass
    conexionesvuln["segura"] = conexionesvuln["segura"] == 1
    conexionesvuln["num_conexiones"] = conexionesvuln["ip"].size
    conexionesvuln = conexionesvuln.groupby(["segura"]).agg({"segura": "first", "num_conexiones": "sum"})
    # print(conexionesvuln)
    fig = px.bar(conexionesvuln, x='segura', y='num_conexiones', title='Media de conexiones')
    fig.show()

    # ----- 4.5 NUMERO DE CONTRASEÑAS COMPROMETIDAS / NO COMPROMETIDAS -----
    datafreim_contrasenas = datafreim_userpass.drop(
        columns=["fecha", "telefono", "ip", "provincia", "permisos", "total", "phising", "clicados"])
    datafreim_contrasenas["numero"] = datafreim_contrasenas["segura"]
    datafreim_contrasenas["segura"] = datafreim_contrasenas["segura"] == 0
    # print(datafreim_contrasenas)

    comp_y_nocomp = datafreim_contrasenas.groupby(["segura"]).agg({"segura": "first", "numero": "size"})
    # print(comp_y_nocomp)

    fig = px.pie(comp_y_nocomp, values='numero', names='segura',
                 title='Número de contraseñas comprometidas vs no comprometidas')
    fig.show()
    #### --------- PRÁCTICA 2 EJERCICIO 2 -------- ####
    print(criticos)
    top5criticos = criticos.head(5)
    print(top5criticos)

    listaTop5Criticos = list(top5criticos.index)
    print(listaTop5Criticos)


    # top5pagcriticas
    con.close()
    return render_template('index.html', ejer2=ejer2, ejer3=ejer3, practica2ej2=listaTop5Criticos)

    # con.close()
    # return render_template('index.html', ejer2=ejer2, ejer3=ejer3)


app.run(debug=True)
