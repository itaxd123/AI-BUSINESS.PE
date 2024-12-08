import os
import re
import pandas as pd
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import folium
from folium.plugins import HeatMap
from gtts import gTTS  # Librería para convertir texto a voz

# Configuración del cliente OpenAI
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Variables globales
excel_data = None
txt_data = None
use_excel_data = False
use_txt_data = False

@app.route("/generaexcel", methods=["POST"])
def generaExcel():    

    #Vamos a pasar  nuestro txt a un txt con solo la latitud y longitud
    #input_file, va a ser nuestro txt de entrada y output_file es nuestro txt de salida 
    def extraer_coordenadas_limpias(input_file, output_file):
        with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
            # Escribe el encabezado al inicio del archivo
            outfile.write("LATITUD, LONGITUD\n")
            for line in infile:
                # Usamos una expresión regular para encontrar "LATITUD: valor" y "LONGITUD: valor"
                matches = re.findall(r"LATITUD:\s*(-?\d+,\d+).*?LONGITUD:\s*(-?\d+,\d+)", line)
                for lat, lon in matches:
                    # Reemplaza la coma por un punto para convertir las coordenadas en números flotantes
                    lat = lat.replace(',', '.')
                    lon = lon.replace(',', '.')
                    
                    # Convierte las coordenadas a tipo flotante (números decimales)
                    try:
                        lat = float(lat)
                        lon = float(lon)
                        # Escribe las coordenadas como números en el archivo de salida
                        outfile.write(f"{lat}, {lon}\n")
                    except ValueError:
                        continue  # Si la conversión falla, se omite la línea
        print(f"Coordenadas extraídas y guardadas en '{output_file}'")

    # Pedimos la ruta de entrada y salida
    input_file = 'uploads/lote01.txt'  # Archivo original
    output_file = 'uploads/solo_coordenadas6.txt'  # Archivo para las coordenadas limpias

    # Llamamos a nuestra función 
    extraer_coordenadas_limpias(input_file, output_file) 

    # Definir nuestro archivo a importar
    filename = "uploads/solo_coordenadas6.txt"  # Mandamos nuestro txt

    data = open(filename, "r", encoding="utf-8")  # Abrimos nuestro archivo txt
    read_data = data.read()  # Creamos una variable a leer

    # Función para procesar los datos
    def transicion_data(strData):  
        data_array = []
        isTransaction = False
        for line in strData.split("\n"):
            if 'LATITUD' in line or isTransaction == True:  # Buscar líneas con "LATITUD"
                isTransaction = True
                data_line = line.split(", ")  # Dividir la línea por ", "
                data_array.append(data_line)  # Agregar la línea procesada al array

        df = pd.DataFrame(data_array)
        df.columns = df.iloc[0]  # Nuestra columna 0 son nuestros cabezales
        df = df.drop([0])  # Una vez se vuelva cabecera lo eliminamos de las líneas en la tabla
        df = df.dropna()  # Eliminamos las filas con valores vacíos

        # Convertir las columnas LATITUD y LONGITUD a números (float)
        df['LATITUD'] = pd.to_numeric(df['LATITUD'], errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'], errors='coerce')

        # Guardamos el DataFrame a un archivo Excel
        df.to_excel("uploads/Mapa_altitudylongitud2.2.xlsx", sheet_name="mapa", index=False)  # index=False para no escribir índices en el archivo
        return df  # Devolvemos los datos procesados 

    # Procesar los datos
    InforData = transicion_data(read_data)
            
    # Cargar datos desde el archivo Excel
    archivo_excel = "uploads/Mapa_altitudylongitud2.1.xlsx"  # Cambia por la ruta de tu archivo
    datos = pd.read_excel(archivo_excel)

    # Crear un mapa base centrado en Lima
    mapa = folium.Map(location=[-12.0464, -77.0428], zoom_start=12)

    # Agregar marcadores individuales por cada emergencia
    colores = {
        "Miraflores": "red",
        "San Isidro": "green",
        "Surco": "blue",
    }
    for _, fila in datos.iterrows():
        folium.Marker(
            location=[fila['LATITUD'], fila['LONGITUD']],
            popup=(
                f"<b>Nombre:</b> {fila['Nombre']}<br>"
                f"<b>Tipo:</b> {fila['Tipo de Emergencia']}<br>"
                f"<b>Distrito:</b> {fila['Distrito']}"
            ),
            icon=folium.Icon(color=colores.get(fila['Distrito'], "gray")),
        ).add_to(mapa)


    # Crear un mapa de calor basado en las coordenadas
    puntos_calor = datos[['LATITUD', 'LONGITUD']].values.tolist()
    HeatMap(puntos_calor).add_to(mapa)

    # Guardar el mapa en un archivo HTML
    mapa.save("static/mapa_calor.html")
    print("Mapa generado: mapa_calor.html")
    return {
        "1" : 1
    }


# Función para limpiar texto
def limpiar_texto(texto):
    texto = re.sub(r"\[.*?\]", "", texto)  # Eliminar etiquetas como [Inaudible]
    texto = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ,.!? ]", "", texto)  # Caracteres irrelevantes
    texto = re.sub(r"\s+", " ", texto).strip()  # Quitar espacios redundantes
    return texto

# Leer y procesar archivos .txt
def procesar_txt(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        contenido = f.read()
    return limpiar_texto(contenido)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    global excel_data, txt_data, use_excel_data, use_txt_data

    if "files" not in request.files:
        return jsonify({"error": "No se proporcionaron archivos"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No se seleccionaron archivos"}), 400

    try:
        for file in files:
            # Guardar archivo
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)

            if file.filename.endswith(".xlsx"):
                # Procesar archivo Excel
                df = pd.read_excel(filepath)
                excel_data = df  # Guardar los datos procesados globalmente
                use_excel_data = True

            elif file.filename.endswith(".txt"):
                # Procesar archivo .txt
                if txt_data is None:
                    txt_data = ""  # Inicializar txt_data si es el primer archivo
                txt_data += procesar_txt(filepath) + "\n"
                use_txt_data = True
                print('txt_data')
                print(txt_data)

            else:
                return jsonify({"error": f"Tipo de archivo no soportado: {file.filename}"}), 400

        return jsonify({"message": "Archivos cargados exitosamente. Configura si deseas usarlos como contexto para responder preguntas."})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/use_context", methods=["POST"])
def use_context():
    global use_excel_data, use_txt_data
    data = request.json
    use_excel = data.get("use_excel")
    use_txt = data.get("use_txt")

    if use_excel is not None:
        use_excel_data = use_excel.lower() == "sí"

    if use_txt is not None:
        use_txt_data = use_txt.lower() == "sí"

    return jsonify({"message": "Configuración actualizada para el uso de contexto."})

@app.route("/ask", methods=["POST"])
def ask():
    global excel_data, txt_data, use_excel_data, use_txt_data

    data = request.json
    question = data.get("question")
    if not question:
        return jsonify({"error": "No se proporcionó una pregunta"}), 400

    try:
        context = ""

        # Combinar datos de Excel y .txt si ambos están habilitados
        if use_excel_data and excel_data is not None:
            context += excel_data.to_string(index=False)

        if use_txt_data and txt_data is not None:
            context += f"\n{txt_data}"
        print('context')
        print(context)
        if not context:
            return jsonify({"error": "No hay contexto disponible para responder la pregunta."}), 400

        # Generar respuesta con OpenAI
        messages = [
            {"role": "system", "content": "Eres un asistente que responde preguntas basado en los datos proporcionados."},
            {"role": "user", "content": f"Contexto: {context}\nPregunta: {question}"}
        ]
        completion = client.chat.completions.create(
            model="meta/llama-3.1-405b-instruct",
            messages=messages,
            temperature=0.2,
            top_p=0.7,
            max_tokens=1024,
            stream=True
        )

        valor = ""
        for chunk in completion:
            if chunk.choices[0].delta.content is not None:
                valor += chunk.choices[0].delta.content
        print('valor')
        print(valor)
        # return jsonify({"answer": valor})
        
        # Generar el archivo de audio para la respuesta
        audio_file = text_to_speech(valor)
        return jsonify({"answer": valor, "audio_file": audio_file})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Función para convertir el texto en voz y guardarlo como archivo MP3 en la carpeta 'static'
def text_to_speech(text):
    # Generar el archivo de audio
    tts = gTTS(text, lang='es')
    
    # Crear un nombre de archivo único en la carpeta estática
    audio_filename = os.path.join('static', 'audio.mp3')
    tts.save(audio_filename)
    
    return 'audio.mp3'

# Ruta para servir el archivo de audio generado
@app.route('/audio/<filename>')
def audio(filename):
    # Devolver el archivo de audio desde la carpeta estática
    return send_from_directory('static', filename)


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
