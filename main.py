# This is a sample Python script.
import numpy as np
from dotmap import DotMap
from flask import Flask, render_template
import sqlite3
import json
import pandas as pd

app = Flask(__name__)


# cur.execute('CREATE TABLE IF NOT EXISTS usuario(name text, age number )')


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
        cookies = entry[url]["cookies"] == 1
        aviso = entry[url]["aviso"] == 1
        proteccion_de_datos = entry[url]["proteccion_de_datos"] == 1
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
    print(datafreim)
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
        "mediafecha": round(mediafecha,2),
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
    # usuariosperm_nan = usuariosperm.
    usuariosperm_mediana = usuariosperm.median()["total"]
    usuariosperm_media = usuariosperm.mean()["total"]
    usuariosperm_varianza = usuariosperm.var()["total"]
    usuariosperm_max = usuariosperm.max()["total"]
    usuariosperm_min = usuariosperm.min()["total"]

    adminperm_num = adminperm.shape[0]
    # usuariosperm_nan = usuariosperm
    adminperm_mediana = adminperm.median()["total"]
    adminperm_media = adminperm.mean()["total"]
    adminperm_varianza = adminperm.var()["total"]
    adminperm_max = adminperm.max()["total"]
    adminperm_min = adminperm.min()["total"]

    mayor200f_num = mayor200.shape[0]
    # usuariosperm_nan = usuariosperm
    mayor200f_mediana = mayor200.median()["total"]
    mayor200f_media = mayor200.mean()["total"]
    mayor200f_varianza = mayor200.var()["total"]
    mayor200f_max = mayor200.max()["total"]
    mayor200f_min = mayor200.min()["total"]

    menor200f_num = menor200.shape[0]
    # usuariosperm_nan = usuariosperm
    menor200f_mediana = menor200.median()["total"]
    menor200f_media = menor200.mean()["total"]
    menor200f_varianza = menor200.var()["total"]
    menor200f_max = menor200.max()["total"]
    menor200f_min = menor200.min()["total"]
    con.close()

    ejer3 = {
        "usuario_observaciones" : usuariosperm_num,
        "usuario_ausentes" : -1,
        "usuario_mediana" : round(usuariosperm_mediana, 2),
        "usuario_media" : round(usuariosperm_media,2),
        "usuario_varianza" : round(usuariosperm_varianza,2),
        "usuario_max" : usuariosperm_max,
        "usuario_min" : usuariosperm_min,
        "admin_observaciones" : adminperm_num,
        "admin_ausentes" : -1,
        "admin_mediana" : round(adminperm_mediana,2),
        "admin_media" : round(adminperm_media,2),
        "admin_varianza" : round(adminperm_varianza, 2),
        "admin_max" : adminperm_max,
        "admin_min" : adminperm_min,
        "mayor200_observaciones" : round(mayor200f_num,2),
        "mayor200_ausentes" : -1,
        "mayor200_mediana" : round(mayor200f_mediana,2),
        "mayor200_media" : round(mayor200f_media,2),
        "mayor200_varianza" : round(mayor200f_varianza,2),
        "mayor200_max" : mayor200f_max,
        "mayor200_min" : mayor200f_min,
        "menor200_observaciones" : menor200f_num,
        "menor200_ausentes" : -1,
        "menor200_mediana" : round(menor200f_mediana, 2),
        "menor200_media" : round(menor200f_media, 2),
        "menor200_varianza" : round(menor200f_varianza, 2),
        "menor200_max" : menor200f_max,
        "menor200_min" : menor200f_min
    }
    ejer3 = DotMap(ejer3)

    return render_template('index.html', ejer2=ejer2, ejer3=ejer3)
    # return "<h1>Ejercicio 2:</h1><p>Numero de usuarios = " + str(usuarios) + \
    #        "<br>Fecha:<ul><li>Media = "+str(mediafecha)+"</li><li>Desviacion = "\
    #        +str(desviacionfecha)+"</li><li>Maximo = "+str(maxfecha)+"</li><li>Minimo = "+str(minfecha)+"</li></ul>IPs:<ul><li>Media = "+str(mediaips)+"</li><li>Desviacion = "\
    #        +str(desviacionips)+"</li></ul>Emails:<ul><li>Media = "+str(mediaemails)+"</li><li>Desviacion = "+str(desviacionemails)+"</li><li>Maximo = "\
    #        +str(maxemails)+"</li><li>Minimo = "+str(minemails)+"</li></ul></p><h1>Ejercicio 3:</h1>"


# Press the green button in the gutter to run the script.
app.run(debug=True)
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
