# This is a sample Python script.
import numpy as np
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
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
    original = datafreim.groupby(["name"], dropna=True).agg(
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

    # print(datafreim)
    # cur.execute('SELECT COUNT(*) FROM users u JOIN ips i ON u.name=i.name WHERE u.provincia != "None" AND '
    #             'u.telefono != "None" AND u.name LIKE "%.%" AND i.ip LIKE "%.%.%.%"')
    # usuarios = cur.fetchall()[0][0]
    # print(usuarios)
    # cur.close()
    con.close()
    return "<p>Numero de usuarios = " + str(usuarios)+\
           "<br>Fecha:<ul><li>Media = "+str(mediafecha)+"</li><li>Desviacion = "\
           +str(desviacionfecha)+"</li><li>Maximo = "+str(maxfecha)+"</li><li>Minimo = "+str(minfecha)+"</li></ul>IPs:<ul><li>Media = "+str(mediaips)+"</li><li>Desviacion = "\
           +str(desviacionips)+"</li></ul>Emails:<ul><li>Media = "+str(mediaemails)+"</li><li>Desviacion = "+str(desviacionemails)+"</li><li>Maximo = "\
           +str(maxemails)+"</li><li>Minimo = "+str(minemails)+"</li></ul></p>"


# Press the green button in the gutter to run the script.
app.run(debug=True)
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
