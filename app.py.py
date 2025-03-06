import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==============================
# CONEXIÓN A GOOGLE SHEETS
# ==============================
SHEET_ID = "1xK3aCqaRSRyWvTYxXgYdwuejO4IydYh42Xykzi0slEo"
NOMBRE_HOJA = 1928091719
NOMBRE_HOJA_DESPACHOS = "Despachos"

scope = ["https://spreadsheets.google.com/feeds", 
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", 
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

try:
    sheet = client.open_by_key(SHEET_ID)
    hoja_ingresos = sheet.get_worksheet_by_id(NOMBRE_HOJA)
    hoja_despachos = sheet.worksheet(NOMBRE_HOJA_DESPACHOS)
except gspread.exceptions.WorksheetNotFound:
    hoja_despachos = sheet.add_worksheet(title=NOMBRE_HOJA_DESPACHOS, rows="1000", cols="8")
    hoja_despachos.append_row(["N° Guía", "Oficina", "Fecha", "Código", "Descripción", "Cantidad", "Folio Inicial", "Folio Final"])

# ==============================
# FUNCIONES
# ==============================
def obtener_numero_guia():
    try:
        data = hoja_despachos.col_values(1)
        return str(int(data[-1]) + 1) if data else "1"
    except:
        return "1"

def cargar_productos():
    try:
        data = hoja_ingresos.get_all_records()
        df = pd.DataFrame(data)
        return dict(zip(df["Código"], df["Descripción"]))
    except:
        return {}

productos = cargar_productos()

def guardar_despacho(oficina, guia, fecha, datos):
    for row in datos:
        hoja_despachos.append_row([guia, oficina, fecha] + row)

def generar_pdf(oficina, guia, fecha, datos):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    
    nombre_archivo = f"Guia_{guia}_Oficina_{oficina.replace(' ', '_')}.pdf"
    c = canvas.Canvas(nombre_archivo, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 12)
    c.drawString(200, height - 130, f"Oficina: {oficina}")
    c.drawString(200, height - 150, f"Guía N°: {guia}")
    c.drawString(400, height - 150, f"Fecha: {fecha}")
    
    data = [["Código", "Descripción", "Cantidad", "Folio Inicial", "Folio Final"]] + datos
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, height - 350)
    c.save()
    return nombre_archivo

# ==============================
# INTERFAZ WEB (DASH)
# ==============================
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Guía de Despacho"),
    dcc.Dropdown(id='oficina', options=[{'label': o, 'value': o} for o in ["Bulnes", "Chillan", "San Carlos"]], value="Bulnes"),
    dcc.Input(id='guia', type='text', value=obtener_numero_guia(), disabled=True),
    dcc.DatePickerSingle(id='fecha', date=datetime.today().strftime('%Y-%m-%d')),
    dash_table.DataTable(
        id='tabla',
        columns=[
            {'name': 'Código', 'id': 'codigo'},
            {'name': 'Descripción', 'id': 'descripcion'},
            {'name': 'Cantidad', 'id': 'cantidad', 'type': 'numeric'},
            {'name': 'Folio Inicial', 'id': 'folio_inicial'},
            {'name': 'Folio Final', 'id': 'folio_final'}
        ],
        data=[{'codigo': '', 'descripcion': '', 'cantidad': '', 'folio_inicial': '', 'folio_final': ''}],
        editable=True,
        row_deletable=True
    ),
    html.Button('Añadir Fila', id='add-row', n_clicks=0),
    html.Button('Guardar Despacho', id='guardar', n_clicks=0),
    html.Button('Generar PDF', id='generar_pdf', n_clicks=0),
    html.Div(id='output')
])

@app.callback(
    Output('tabla', 'data'),
    Input('add-row', 'n_clicks'),
    State('tabla', 'data')
)
def agregar_fila(n, data):
    data.append({'codigo': '', 'descripcion': '', 'cantidad': '', 'folio_inicial': '', 'folio_final': ''})
    return data

@app.callback(
    Output('output', 'children'),
    Input('guardar', 'n_clicks'),
    State('oficina', 'value'),
    State('guia', 'value'),
    State('fecha', 'date'),
    State('tabla', 'data')
)
def guardar(n, oficina, guia, fecha, data):
    if n > 0:
        guardar_despacho(oficina, guia, fecha, [list(d.values()) for d in data if d['codigo']])
        return "Despacho guardado correctamente."

@app.callback(
    Output('output', 'children', allow_duplicate=True),
    Input('generar_pdf', 'n_clicks'),
    State('oficina', 'value'),
    State('guia', 'value'),
    State('fecha', 'date'),
    State('tabla', 'data'),
    prevent_initial_call=True
)
def generar_pdf_callback(n, oficina, guia, fecha, data):
    if n > 0:
        archivo = generar_pdf(oficina, guia, fecha, [list(d.values()) for d in data if d['codigo']])
        return f"PDF generado: {archivo}"

if __name__ == '__main__':
    app.run_server(debug=True)
