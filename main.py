import numpy as np
from dotmap import DotMap
from flask import Flask, render_template
import sqlite3
import json
import pandas as pd
import plotly.express as px
import hashlib

app = Flask(__name__)


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
    return "<p>Hello World</p>"


@app.route('/hello')
@app.route('/hello/<name>')
def helloname(name=None):
    return "<p>Hello " + name + "</p>"


@app.route('/func')
def func():
    con = sqlite3.connect("example2.db", timeout=10)
    con.execute("PRAGMA foreign_keys = 1")
    cur = con.cursor()
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
        # print(
        #     "Name: {}\nTelefono: {}\nContrasena: {}\nProvincia: {}\nPermisos: {}\nEmails: {}\nFechas: {}\nIps: {}\n".format(
        #         name, telefono, contrasena, provincia, permisos, emails, fechas, ips))
        pass
    con.commit()
    cur.close()

    return "hola"


@app.route('/dataframe')
def dataframe():
    con = sqlite3.connect("example2.db", timeout=10)
    # con.execute("PRAGMA foreign_keys = 1")
    # cur = con.cursor()
    query = pd.read_sql_query(
        'SELECT u.*, i.ip, i.fecha, e.total, e.phising, e.clicados FROM users u JOIN ips i ON u.name=i.name '
        'JOIN emails e ON u.name=e.name WHERE u.provincia != "None" AND '
        'u.telefono != "None" AND u.name LIKE "%.%" AND i.ip LIKE "%.%.%.%"', con, "name")
    datafreim = pd.DataFrame(query,
                             columns=["name", "telefono", "contrasena", "provincia", "permisos", "ip", "fecha", "total",
                                      "phising", "clicados"])

    datafreim = datafreim.drop("name", axis=1)
    print(datafreim)
    original = datafreim.groupby(["name"], dropna=False).agg(
        {"fecha": np.array, "ip": np.array, "telefono": "first", "contrasena": "first", "provincia": "first",
         "permisos": "first", "total": "first", "phising": "first", "clicados": "first"})

    fecha = datafreim.groupby(["name"], dropna=True).agg(
        {"fecha": "count"})
    ips = datafreim.groupby(["name"], dropna=True).agg(
        {"ip": "count"})
    emails = datafreim.groupby(["name"], dropna=True).agg(
        {"total": "first"})
    mediafecha = fecha.mean()["fecha"]
    desviacionfecha = fecha.std()["fecha"]
    mediaips = ips.mean()["ip"]
    desviacionips = ips.std()["ip"]
    mediaemails = emails.mean()["total"]
    desviacionemails = emails.std()["total"]
    usuarios = original.shape[0]
    maxfecha = fecha.max()["fecha"]
    minfecha = fecha.min()["fecha"]
    maxemails = emails.max()["total"]
    minemails = emails.min()["total"]

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

    usuariosperm = original.loc[original.permisos == "False", ['total', 'phising', 'clicados']]
    adminperm = original.loc[original.permisos == "True", ['total', 'phising', 'clicados']]
    mayor200 = original.loc[original.total >= 200, ['total', 'phising', 'clicados']]
    menor200 = original.loc[original.total < 200, ['total', 'phising', 'clicados']]
    print(usuariosperm)
    print(adminperm)
    print(mayor200)
    print(menor200)
    usuariosperm_num = usuariosperm.shape[0]
    # usuariosperm_nan = usuariosperm
    usuariosperm_mediana = usuariosperm.median()["phising"]
    usuariosperm_media = usuariosperm.mean()["phising"]
    usuariosperm_varianza = usuariosperm.var()["phising"]
    usuariosperm_max = usuariosperm.max()["phising"]
    usuariosperm_min = usuariosperm.min()["phising"]

    adminperm_num = adminperm.shape[0]
    # usuariosperm_nan = usuariosperm
    adminperm_mediana = adminperm.median()["phising"]
    adminperm_media = adminperm.mean()["phising"]
    adminperm_varianza = adminperm.var()["phising"]
    adminperm_max = adminperm.max()["phising"]
    adminperm_min = adminperm.min()["phising"]

    mayor200f_num = mayor200.shape[0]
    # usuariosperm_nan = usuariosperm
    mayor200f_mediana = mayor200.median()["phising"]
    mayor200f_media = mayor200.mean()["phising"]
    mayor200f_varianza = mayor200.var()["phising"]
    mayor200f_max = mayor200.max()["phising"]
    mayor200f_min = mayor200.min()["phising"]

    menor200f_num = menor200.shape[0]
    # usuariosperm_nan = usuariosperm
    menor200f_mediana = menor200.median()["phising"]
    menor200f_media = menor200.mean()["phising"]
    menor200f_varianza = menor200.var()["phising"]
    menor200f_max = menor200.max()["phising"]
    menor200f_min = menor200.min()["phising"]

    ejer3 = {
        "usuario_observaciones": usuariosperm_num,
        "usuario_ausentes": -1,
        "usuario_mediana": round(usuariosperm_mediana, 2),
        "usuario_media": round(usuariosperm_media, 2),
        "usuario_varianza": round(usuariosperm_varianza, 2),
        "usuario_max": usuariosperm_max,
        "usuario_min": usuariosperm_min,
        "admin_observaciones": adminperm_num,
        "admin_ausentes": -1,
        "admin_mediana": round(adminperm_mediana, 2),
        "admin_media": round(adminperm_media, 2),
        "admin_varianza": round(adminperm_varianza, 2),
        "admin_max": adminperm_max,
        "admin_min": adminperm_min,
        "mayor200_observaciones": round(mayor200f_num, 2),
        "mayor200_ausentes": -1,
        "mayor200_mediana": round(mayor200f_mediana, 2),
        "mayor200_media": round(mayor200f_media, 2),
        "mayor200_varianza": round(mayor200f_varianza, 2),
        "mayor200_max": mayor200f_max,
        "mayor200_min": mayor200f_min,
        "menor200_observaciones": menor200f_num,
        "menor200_ausentes": -1,
        "menor200_mediana": round(menor200f_mediana, 2),
        "menor200_media": round(menor200f_media, 2),
        "menor200_varianza": round(menor200f_varianza, 2),
        "menor200_max": menor200f_max,
        "menor200_min": menor200f_min
    }
    ejer3 = DotMap(ejer3)

    print("--------- EJERCICIO 4 ----------")

    # ----- PAGINAS WEB CON POLITICAS DESACTUALIZADAS -------
    query_legal = pd.read_sql_query('SELECT url, cookies, aviso, proteccion_de_datos, creacion FROM legal', con)
    datafreim_legal = pd.DataFrame(query_legal, columns=["url", "cookies", "aviso", "proteccion_de_datos", "creacion"])

    print(datafreim_legal)
    datafreim_legal["inseguro"] = datafreim_legal["cookies"] + datafreim_legal["aviso"] + datafreim_legal[
        "proteccion_de_datos"]
    datafreim_legal = datafreim_legal.dropna(axis=1)
    dataframe_legal = datafreim_legal.sort_values(by=["inseguro"], ascending=True, inplace=True)
    paginas_inseguras = datafreim_legal.head(5)
    paginas_inseguras = paginas_inseguras.drop(columns=["inseguro"])
    # paginas_inseguras["url"] = paginas_inseguras.loc[[], "url"]
    print(paginas_inseguras)

    grafico_paginas = px.bar(paginas_inseguras, x="url", y=["cookies", "aviso", "proteccion_de_datos"],
                             title="Páginas con políticas desactualizadas")
    grafico_paginas.show()

    # ----- MOSTRAR SEGÚN AÑO WEBS QUE CUMPLEN POLITICA PRIVACIDAD VS NO -------
    politicas = datafreim_legal
    # Si son inseguros = 1, si son seguros = 0
    politicas["inseguro"] = (politicas["inseguro"] < 3) * 1
    politicas["seguro"] = (politicas["inseguro"] == 0) * 1
    print("seguro o inseguro")
    print(politicas)
    politicas = politicas.drop(columns=["cookies", "aviso", "proteccion_de_datos"])
    politicas = politicas.groupby(["creacion"]).agg(
        {"inseguro": "sum", "seguro": "sum", "url": "first", "creacion": "first"})
    print(politicas)

    fig = px.line(politicas, x="creacion", y="inseguro", title="Nº de webs inseguras")
    fig.show()
    fig = px.line(politicas, x="creacion", y="seguro", title="Nº de webs seguras")
    fig.show()

    # SEPARAMOS POR CONTRASEÑAS VULNERADAS

    diccionario = open("data/diccionario.txt", "r")
    dict_hashes = diccionario.read().split("\n")
    # print(dict_hashes)
    diccionario.close()

    query_userpass = pd.read_sql_query('SELECT name, contrasena FROM users', con)
    datafreim_userpass = pd.DataFrame(query_userpass, columns=["name", "contrasena"])
    datafreim_userpass["segura"] = (datafreim_userpass["contrasena"].isin(dict_hashes))*1
    print(datafreim_userpass)

    # MOSTRAR 10 USUARIOS MÁS CRÍTICOS

    # MEDIA DE CONEXIONES CON CONTRASEÑA VULNERABLE VS NO VULN

    # NUMERO DE CONTRASEÑAS COMPROMETIDAS / NO COMPROMETIDAS
    #comprometidas = datafreim_userpass.groupby(["creacion"]).agg(  {"inseguro": "sum", "seguro": "sum", "url": "first", "creacion": "first"})



    con.close()
    return render_template('index.html', ejer2=ejer2, ejer3=ejer3)


# Press the green button in the gutter to run the script.
app.run(debug=True)
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
