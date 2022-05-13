import numpy as np
import matplotlib.pyplot as plt
from dotmap import DotMap
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response
import sqlite3
import json
import pandas as pd
import plotly.express as px
import plotly
import requests as req
from sklearn import linear_model, tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score
import graphviz
from sklearn.tree import export_graphviz
from subprocess import call
import PIL
import pdfkit

app = Flask(__name__)


@app.route('/static/<path:path>')
def send_report(path):
    return send_from_directory('static', path)


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


def df_datafreim():
    con = sqlite3.connect("example2.db", timeout=10)
    query = pd.read_sql_query(
        'SELECT u.*, i.ip, i.fecha, e.total, e.phising, e.clicados FROM users u JOIN ips i ON u.name=i.name '
        'JOIN emails e ON u.name=e.name WHERE u.provincia != "None" AND '
        'u.telefono != "None" AND i.ip LIKE "%.%.%.%"', con, "name")
    datafreim = pd.DataFrame(query,
                             columns=["name", "telefono", "contrasena", "provincia", "permisos", "ip", "fecha", "total",
                                      "phising", "clicados"])

    datafreim = datafreim.drop("name", axis=1)
    con.close()
    return datafreim


def df_original():
    datafreim = df_datafreim()
    original = datafreim.groupby(["name"], dropna=False).agg(
        {"fecha": np.array, "ip": np.array, "telefono": "first", "contrasena": "first", "provincia": "first",
         "permisos": "first", "total": "first", "phising": "first", "clicados": "first"})
    return original


def diccionarioHashes():
    diccionario = open("data/diccionario.txt", "r")
    dict_hashes = diccionario.read().split("\n")
    diccionario.close()
    return dict_hashes


def df_legal():
    con = sqlite3.connect("example2.db", timeout=10)
    query_legal = pd.read_sql_query('SELECT url, cookies, aviso, proteccion_de_datos, creacion FROM legal', con)
    datafreim_legal = pd.DataFrame(query_legal, columns=["url", "cookies", "aviso", "proteccion_de_datos", "creacion"])
    # print(datafreim_legal)

    # ----- 4.2 PAGINAS WEB CON POLITICAS DESACTUALIZADAS -------
    datafreim_legal["inseguro"] = datafreim_legal["cookies"] + datafreim_legal["aviso"] + datafreim_legal[
        "proteccion_de_datos"]
    datafreim_legal = datafreim_legal.dropna(axis=1)
    datafreim_legal.sort_values(by=["inseguro"], ascending=True, inplace=True)
    con.close()
    return datafreim_legal


@app.route('/topPages', methods=['GET'])
def topXpaginasOriginal():
    n = int(request.args.get("n"))
    pages = topXpaginasVuln(n)
    urls = list(pages["url"])
    jsontext = json.dumps({"urls": urls, "num": n})
    return jsontext


def topXpaginasVuln(n):
    return df_legal().head(n)


@app.route('/topUsers', methods=['GET'])
def topXusuariosOriginal():
    n = int(request.args.get("n"))
    users = topXusuarios(n)
    names = list(users.index)
    probClick = list(users["prob-clic"])
    jsontext = json.dumps({"names": names, "num": n, "probClick": probClick})
    return jsontext


def topXusuarios(n):
    # SEPARAMOS POR CONTRASEÑAS VULNERADAS
    # Diccionario con los hashes comprometidos de los usuarios
    # diccionario = open("data/diccionario.txt", "r")
    # dict_hashes = diccionario.read().split("\n")
    # diccionario.close()
    dict_hashes = diccionarioHashes()

    datafreim_userpass = df_original()
    # print(datafreim_userpass)
    datafreim_userpass["segura"] = (datafreim_userpass["contrasena"].isin(dict_hashes)) * 1
    # print(datafreim_userpass)

    # Dataframes de usuarios comprometidos  / no comprometidos
    comprometidos = datafreim_userpass[datafreim_userpass.segura == 1]
    nocomprometidos = datafreim_userpass[datafreim_userpass.segura == 0]

    # -----  X USUARIOS MÁS CRÍTICOS -----
    comprometidos["prob-clic"] = comprometidos["clicados"] / comprometidos["phising"]
    criticos = comprometidos
    criticos.sort_values(by=["prob-clic"], ascending=False, inplace=True)
    criticos = criticos.head(n)
    print(criticos)
    return criticos


@app.route("/cveinfo", methods=['GET'])
def cve_info():
    data = req.get("https://cve.circl.lu/api/last/10")
    return jsonify(data.json())


def linearRegression(training_x, training_y, users_x, users_y, datos_reales):
    # Regresión Lineal
    regr = linear_model.LinearRegression()
    regr.fit(training_x, training_y)
    prediccion = regr.predict(users_x)

    prediccionv2 = []
    for i in range(len(prediccion)):
        if prediccion[i] >= 0.5:
            prediccionv2.append(int(1))
        else:
            prediccionv2.append(int(0))

    usersxv2 = []
    for i in range(len(users_x)):
        if users_x[i][0] == 0:
            usersxv2.append(0)
        else:
            usersxv2.append(users_x[i][1] / users_x[i][0])

    a = r2_score(users_y, prediccionv2)
    b = regr.intercept_
    recta = (np.array(usersxv2) * a) + b

    plt.scatter(usersxv2, users_y, color="black")
    plt.plot(recta, usersxv2, color="purple", linewidth=2)
    plt.xticks(())
    plt.yticks(())
    plt.show()

    print("REGRESIÓN LINEAL")
    print("Mean squared error: %.2f" % mean_squared_error(users_y, prediccionv2))
    print("Porcentaje de aciertos: %.2f" % accuracy_score(users_y, prediccionv2))

    prediccion_real = regr.predict(datos_reales)
    prediccion_realv2 = []
    for i in range(len(prediccion_real)):
        if prediccion_real[i] >= 0.5:
            prediccion_realv2.append(int(1))
        else:
            prediccion_realv2.append(int(0))

    print("Predicción sobre los datos reales: hay", prediccion_realv2.count(1), " usuarios vulnerables y ",
          prediccion_realv2.count(0), " no vulnerables")
    print("")

    return [mean_squared_error(users_y, prediccionv2), accuracy_score(users_y, prediccionv2), prediccion_realv2.count(1), prediccion_realv2.count(0)]


def decisionTree(training_x, training_y, users_x, users_y, datos_reales):
    # Árbol de decisión
    arbol = tree.DecisionTreeClassifier()
    clf = arbol.fit(training_x, training_y)

    res_arbol = arbol.predict(users_x)

    dot_data = tree.export_graphviz(clf, out_file=None)
    graph = graphviz.Source(dot_data)
    graph.render("Árbol")
    dot_data = tree.export_graphviz(clf, out_file=None,
                                    filled=True, rounded=True,
                                    special_characters=True)
    graph = graphviz.Source(dot_data)
    # TODO: graph.render('test.gv', view=True).replace('\\', '/')

    print("ÁRBOL DE DECISIÓN")
    print("Mean squared error: %.2f" % mean_squared_error(users_y, res_arbol))
    print("Porcentaje de aciertos: %.2f" % accuracy_score(users_y, res_arbol))

    prediccion_real = arbol.predict(datos_reales)
    prediccion_realv2 = []
    for i in range(len(prediccion_real)):
        if prediccion_real[i] >= 0.5:
            prediccion_realv2.append(int(1))
        else:
            prediccion_realv2.append(int(0))

    print("Predicción sobre los datos reales: hay", prediccion_realv2.count(1), " usuarios vulnerables y ",
          prediccion_realv2.count(0), " no vulnerables")
    print("")

    return [mean_squared_error(users_y, res_arbol), accuracy_score(users_y, res_arbol),
            prediccion_realv2.count(1), prediccion_realv2.count(0), prediccion_realv2]


def randomForest(training_x, training_y, users_x, users_y, datos_reales):
    # Random Forest
    forest = RandomForestClassifier(max_depth=2, random_state=0, n_estimators=10)
    forest.fit(training_x, training_y)
    # print(str(training_x[0]) + " " + str(training_y[0]))
    res = forest.predict(users_x)

    for i in range(len(forest.estimators_)):
        estimator = forest.estimators_[i]
        export_graphviz(estimator,
                        out_file='tree.dot',
                        rounded=True, proportion=False,
                        precision=2, filled=True)
        call(['dot', '-Tpng', 'tree.dot', '-o', 'tree' + str(i) + '.png', '-Gdpi=600'])

    print("RANDOM FOREST")
    print("Mean squared error: %.2f" % mean_squared_error(users_y, res))
    print("Porcentaje de aciertos: %.2f" % accuracy_score(users_y, res))

    prediccion_real = forest.predict(datos_reales)
    prediccion_realv2 = []
    for i in range(len(prediccion_real)):
        if prediccion_real[i] >= 0.5:
            prediccion_realv2.append(int(1))
        else:
            prediccion_realv2.append(int(0))

    print("Predicción sobre los datos reales: hay", prediccion_realv2.count(1), " usuarios vulnerables y ",
          prediccion_realv2.count(0), " no vulnerables")
    print("")

    return [mean_squared_error(users_y, res), accuracy_score(users_y, res),
            prediccion_realv2.count(1), prediccion_realv2.count(0)]


def IA(predecir2):  # datos para predecir se pasarian aqui (predecir)
    # Abrir y cargar datos
    clases = open("data/users_IA_clases.json")
    predecir = open("data/users_IA_predecir.json")  ##Esta linea fuera cuando carguemos desde parametro
    clasesData = json.load(clases)
    predecirData = json.load(predecir)



    train_x = []
    train_y = []

    for e in clasesData["usuarios"]:
        usuario = e["usuario"]
        phishing = e["emails_phishing_recibidos"]
        clickado = e["emails_phishing_clicados"]
        vulnerable = e["vulnerable"]
        train_x.append([phishing, clickado])
        train_y.append(vulnerable)

    datos_reales = []
    if predecir2:
        predecirData=predecir2
    for e in predecirData["usuarios"]:
        usuario = e["usuario"]
        phishing = e["emails_phishing_recibidos"]
        clickado = e["emails_phishing_clicados"]
        datos_reales.append([phishing, clickado])

    # Separar los datos
    tope = int(len(train_x) * 0.7)
    training_x = train_x[:tope]
    training_y = train_y[:tope]
    users_x = train_x[tope:]
    users_y = train_y[tope:]

    # Entrenar y predecir con los diferentes modelos
    if predecir2:
        return decisionTree(training_x, training_y, users_x, users_y, datos_reales)
    lin = linearRegression(training_x, training_y, users_x, users_y, datos_reales)
    tree = decisionTree(training_x, training_y, users_x, users_y, datos_reales)
    forest = randomForest(training_x, training_y, users_x, users_y, datos_reales)

    return [lin,tree,forest]


@app.route('/checkUsers', methods=['POST'])
def checkUsers():
    archivo = request.files["data"]
    data = archivo.stream.read()
    prediccion = json.loads(data)
    resultados=IA(prediccion)
    print(len(resultados))
    print("resultados IA JSOn: ", resultados)
    for i in range(len(prediccion["usuarios"])):
        prediccion["usuarios"][i]["vulnerable"] = resultados[4][i]
        pass
    salida = {
        "criticos" : resultados[2],
        "no criticos": resultados[3],
        "prediccion": prediccion
    }
    return json.dumps(salida)


# ------------- EJERCICIOS 2, 3 Y 4 -------------
@app.route('/dataframe', methods=['GET'])
def dataframe():

    ia_data = IA(None)
    reg = {
        "aciertos": round(ia_data[0][1],2)*100,
        "error": round(ia_data[0][0],2)*100,
        "numvuln": ia_data[0][2],
        "numnovuln": ia_data[0][3]

    }
    reg = DotMap(reg)

    tree = {
        "aciertos": round(ia_data[1][1],2)*100,
        "error": round(ia_data[1][0],2)*100,
        "numvuln": ia_data[1][2],
        "numnovuln": ia_data[1][3]

    }
    tree = DotMap(tree)

    forest = {
        "aciertos": round(ia_data[2][1],2)*100,
        "error": round(ia_data[2][0],2)*100,
        "numvuln": ia_data[2][2],
        "numnovuln": ia_data[2][3]

    }
    forest = DotMap(forest)

    con = sqlite3.connect("example2.db", timeout=10)

    datafreim = df_datafreim()
    original = df_original()

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
    # query_legal = pd.read_sql_query('SELECT url, cookies, aviso, proteccion_de_datos, creacion FROM legal', con)
    # datafreim_legal = pd.DataFrame(query_legal, columns=["url", "cookies", "aviso", "proteccion_de_datos", "creacion"])
    # # print(datafreim_legal)
    #
    # # ----- 4.2 PAGINAS WEB CON POLITICAS DESACTUALIZADAS -------
    # datafreim_legal["inseguro"] = datafreim_legal["cookies"] + datafreim_legal["aviso"] + datafreim_legal[
    #     "proteccion_de_datos"]
    # datafreim_legal = datafreim_legal.dropna(axis=1)
    # datafreim_legal.sort_values(by=["inseguro"], ascending=True, inplace=True)
    datafreim_legal = df_legal()
    paginas_inseguras = datafreim_legal.head(5)
    # print(paginas_inseguras)
    grafico_paginas = px.bar(paginas_inseguras, x="url", y=["cookies", "aviso", "proteccion_de_datos"],
                             title="Páginas con políticas desactualizadas")
    # grafico_paginas.show()
    auxGrafico2 = plotly.utils.PlotlyJSONEncoder
    grafico4_2 = json.dumps(grafico_paginas, cls=auxGrafico2)

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

    fig41 = px.line(politicas, x="creacion", y="inseguro", title="Nº de webs inseguras")
    # fig1.show()
    auxGrafico4_41 = plotly.utils.PlotlyJSONEncoder
    grafico4_41 = json.dumps(fig41, cls=auxGrafico4_41)

    fig42 = px.line(politicas, x="creacion", y="seguro", title="Nº de webs seguras")
    # fig2.show()
    auxGrafico4_42 = plotly.utils.PlotlyJSONEncoder
    grafico4_42 = json.dumps(fig42, cls=auxGrafico4_42)

    # SEPARAMOS POR CONTRASEÑAS VULNERADAS
    # Diccionario con los hashes comprometidos de los usuarios
    # diccionario = open("data/diccionario.txt", "r")
    # dict_hashes = diccionario.read().split("\n")
    # diccionario.close()

    # datafreim_userpass = original
    # # print(datafreim_userpass)
    # datafreim_userpass["segura"] = (datafreim_userpass["contrasena"].isin(dict_hashes)) * 1
    # # print(datafreim_userpass)
    #
    # # Dataframes de usuarios comprometidos  / no comprometidos
    # comprometidos = datafreim_userpass[datafreim_userpass.segura == 1]
    # nocomprometidos = datafreim_userpass[datafreim_userpass.segura == 0]
    #
    # # ----- 4.1 10 USUARIOS MÁS CRÍTICOS -----
    # comprometidos["prob-clic"] = comprometidos["clicados"] / comprometidos["phising"]
    # criticos = comprometidos
    # criticos.sort_values(by=["prob-clic"], ascending=False, inplace=True)
    # criticos = criticos.head(10)
    # print(criticos)

    criticos = topXusuarios(10)
    fig1 = px.bar(criticos, x=criticos.index, y='prob-clic', title="Top 10 usuarios más críticos")
    # fig.show()
    auxGrafico1 = plotly.utils.PlotlyJSONEncoder
    grafico4_1 = json.dumps(fig1, cls=auxGrafico1)

    # ----- 4.3 MEDIA DE CONEXIONES CON CONTRASEÑA VULNERABLE VS NO VULNERABLE -----
    datafreim_userpass = df_original()
    datafreim_userpass["segura"] = (datafreim_userpass["contrasena"].isin(diccionarioHashes())) * 1
    conexionesvuln = datafreim_userpass
    conexionesvuln["segura"] = conexionesvuln["segura"] == 1
    conexionesvuln["num_conexiones"] = conexionesvuln["ip"].size
    conexionesvuln = conexionesvuln.groupby(["segura"]).agg({"segura": "first", "num_conexiones": "sum"})
    # print(conexionesvuln)
    fig3 = px.bar(conexionesvuln, x='segura', y='num_conexiones', title='Media de conexiones')
    # fig.show()
    auxGrafico3 = plotly.utils.PlotlyJSONEncoder
    grafico4_3 = json.dumps(fig3, cls=auxGrafico3)

    # ----- 4.5 NUMERO DE CONTRASEÑAS COMPROMETIDAS / NO COMPROMETIDAS -----
    datafreim_contrasenas = datafreim_userpass.drop(
        columns=["fecha", "telefono", "ip", "provincia", "permisos", "total", "phising", "clicados"])
    datafreim_contrasenas["numero"] = datafreim_contrasenas["segura"]
    datafreim_contrasenas["segura"] = datafreim_contrasenas["segura"] == 0
    # print(datafreim_contrasenas)

    comp_y_nocomp = datafreim_contrasenas.groupby(["segura"]).agg({"segura": "first", "numero": "size"})
    # print(comp_y_nocomp)

    fig5 = px.pie(comp_y_nocomp, values='numero', names='segura',
                  title='Número de contraseñas comprometidas vs no comprometidas')
    # fig.show()
    auxGrafico5 = plotly.utils.PlotlyJSONEncoder
    grafico4_5 = json.dumps(fig5, cls=auxGrafico5)

    #### --------- PRÁCTICA 2 EJERCICIO 2 -------- ####
    # print(criticos)
    top5criticos = criticos.head(5)
    # print(top5criticos)

    listaTop5Criticos = list(top5criticos.index)
    # print(listaTop5Criticos)

    # print(datafreim_legal)
    top5pagcriticas = datafreim_legal.head(5)
    # print(top5pagcriticas)

    listaTop5PagCriticas = list(top5pagcriticas["url"])
    # print(listaTop5PagCriticas)

    listaTop5Criticos = {
        "usuarios": listaTop5Criticos,
        "paginas": listaTop5PagCriticas
    }

    listaTop5Criticos = DotMap(listaTop5Criticos)

    con.close()

    return render_template('index.html', ejer2=ejer2, ejer3=ejer3, practica2ej2=listaTop5Criticos,
                           grafico4_1=grafico4_1, grafico4_2=grafico4_2, grafico4_3=grafico4_3, grafico4_41=grafico4_41,
                           grafico4_42=grafico4_42, grafico4_5=grafico4_5, reg=reg, forest=forest, tree=tree)
    # con.close()
    # return render_template('index.html', ejer2=ejer2, ejer3=ejer3)


app.run(debug=True)
