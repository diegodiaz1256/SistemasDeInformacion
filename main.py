# This is a sample Python script.
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import json

app = Flask(__name__)


# cur.execute('CREATE TABLE IF NOT EXISTS usuario(name text, age number )')


@app.route('/')
def hello():
    con = sqlite3.connect("example2.db", timeout=10)
    con.execute("PRAGMA foreign_keys = 1")
    cur = con.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS legal(url text primary key, cookies boolean, aviso boolean, proteccion_de_datos boolean, creacion number)')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users(name text primary key, telefono text, contrasena text, provincia text, permisos boolean)')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS emails(name text, total number, phising number, clicados number, foreign key (name) references users (name))')
    cur.execute('CREATE TABLE IF NOT EXISTS ips(name text, ip text, foreign key (name) references users (name))')
    cur.execute('CREATE TABLE IF NOT EXISTS fechas(name text , fecha text, foreign key (name) references users (name))')
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
        print("name: {}\nCookies: {}\nAviso: {}\nProteccion de Datos: {}\ncreacion: {}\n".format(url, cookies, aviso,
                                                                                                 proteccion_de_datos,
                                                                                                 creacion))
    f.close()
    f = open("data/users.json")
    data = json.load(f)
    print(data)
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
        for ip in ips:
            cur.execute('INSERT INTO ips values("{}", "{}")'
                        .format(name, ip))
            pass
        for fecha in fechas:
            cur.execute('INSERT INTO fechas values("{}", "{}")'
                        .format(name, fecha))
        print(
            "Name: {}\nTelefono: {}\nContrasena: {}\nProvincia: {}\nPermisos: {}\nEmails: {}\nFechas: {}\nIps: {}\n".format(
                name, telefono, contrasena, provincia, permisos, emails, fechas, ips))
        pass
    con.commit()
    cur.close()

    return "hola"


@app.route('/dataframe')
def dataframe():
    con = sqlite3.connect("example2.db", timeout=10)
    # con.execute("PRAGMA foreign_keys = 1")
    cur = con.cursor()
    print(cur.execute('SELECT COUNT(*) FROM users'))
    print(cur.execute('SELECT COUNT(*) FROM users'))
    print(cur.fetchmany(1))
    usuarios = cur.fetchall()[0][0]
    cur.close()
    return "numero de usuarios = " + str(usuarios)


# Press the green button in the gutter to run the script.
app.run(debug=True)
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
