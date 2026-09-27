import base64, os, re, struct, requests, urllib3
from datetime import datetime, timedelta, timezone
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

archivo_csv = "historico_diario.csv"

hoy = datetime.now(timezone.utc) - timedelta(hours=5)
ayer = hoy - timedelta(days=1)
fecha_dato = ayer.strftime("%Y-%m-%d")

cota = None
pico = None
fecha_demanda_texto = None

# ---------- 1. COTA DE MAZAR ----------
try:
    url_mazar = "https://generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr/pointValues"
    parametros = {
        "mrid": 30031,
        "fechaInicio": ayer.strftime("%Y-%m-%d") + "T06:00:00.000Z",
        "fechaFin": hoy.strftime("%Y-%m-%d") + "T05:00:00.000Z",
        "fecha": ayer.strftime("%d/%m/%Y") + " 00:00:00"
    }
    resp_mazar = requests.get(url_mazar, params=parametros, verify=False, timeout=15)
    datos_mazar = resp_mazar.json()
    for hora in datos_mazar["items"]:
        if hora["valueedit"] is not None:
            cota = hora["valueedit"]
            break
    print("✅ Cota de Mazar (", fecha_dato, "):", cota)
except Exception as e:
    print("⚠️ No se pudo obtener la cota de Mazar:", e)

# ---------- 2. PICO DE DEMANDA ----------
try:
    url_cenace = "https://www.cenace.gob.ec/info-operativa/InformacionOperativa.htm"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp_cenace = requests.get(url_cenace, headers=headers, verify=False, timeout=20)
    html = resp_cenace.text.replace("\\u002f", "/")

    patron_fecha = r"INFORMACIÓN OPERATIVA DIARIA</h2>.*?<span>([^<]+)</span>"
    fecha_demanda_texto = re.search(patron_fecha, html, re.DOTALL).group(1).strip()

    patron_demanda = r'"name":"DEMANDA NACIONAL".*?"bdata":"([^"]+)"'
    coincidencias = re.findall(patron_demanda, html)
    datos_binarios = base64.b64decode(coincidencias[1])
    valores = struct.unpack(f"<{len(datos_binarios)//8}d", datos_binarios)
    pico = round(max(valores), 1)
    print("✅ Pico de demanda:", pico, "MW —", fecha_demanda_texto)
except Exception as e:
    print("⚠️ No se pudo obtener el dato de CENACE:", e)

# ---------- 3. GUARDAR ----------
nueva_fila = pd.DataFrame([{
    "fecha": fecha_dato,
    "cota_mazar": cota,
    "pico_demanda_mw": pico
}])

if os.path.exists(archivo_csv):
    tabla = pd.read_csv(archivo_csv)
    if fecha_dato in tabla["fecha"].values:
        print(f"⚠️ Ya existe un registro para {fecha_dato}. No se duplicó.")
    else:
        tabla = pd.concat([tabla, nueva_fila], ignore_index=True)
        tabla = tabla.sort_values("fecha").reset_index(drop=True)
        tabla.to_csv(archivo_csv, index=False)
        print("✅ Fila nueva agregada.")
else:
    nueva_fila.to_csv(archivo_csv, index=False)
    print("📝 Archivo creado con el primer registro.")

print("\n--- Historial actual ---")
print(pd.read_csv(archivo_csv))

import json

# ---------- 4. GENERAR BADGE DINÁMICO (status.json) ----------
tabla_final = pd.read_csv(archivo_csv)
ultima_fila = tabla_final.dropna(subset=["cota_mazar"]).iloc[-1]
cota_actual = ultima_fila["cota_mazar"]

NIVEL_CRITICO = 2115
margen = cota_actual - NIVEL_CRITICO

if margen > 20:
    color = "green"
elif margen > 10:
    color = "yellow"
else:
    color = "red"

badge_data = {
    "schemaVersion": 1,
    "label": "Cota Mazar",
    "message": f"{cota_actual} msnm",
    "color": color
}

with open("status.json", "w") as f:
    json.dump(badge_data, f)

print("✅ status.json generado:", badge_data)

# Badge de demanda (usa la última fila con dato de demanda disponible)
ultima_demanda = tabla_final.dropna(subset=["pico_demanda_mw"]).iloc[-1]
demanda_actual = ultima_demanda["pico_demanda_mw"]

if demanda_actual < 4500:
    color_demanda = "green"
elif demanda_actual < 5200:
    color_demanda = "yellow"
else:
    color_demanda = "red"

badge_demanda = {
    "schemaVersion": 1,
    "label": "Demanda pico",
    "message": f"{demanda_actual} MW",
    "color": color_demanda
}

with open("status_demanda.json", "w") as f:
    json.dump(badge_demanda, f)

# ---------- 5. PREDICCIÓN DEL DÍA SIGUIENTE (modelo ingenuo) ----------
archivo_predicciones = "predicciones.csv"

tabla_cota = tabla_final.dropna(subset=["cota_mazar"]).copy()
tabla_demanda = tabla_final.dropna(subset=["pico_demanda_mw"]).copy()

# Tomamos los últimos 5 registros disponibles para calcular la tendencia
ultimos_cota = tabla_cota.tail(5)
if len(ultimos_cota) >= 2:
    cambio_diario_promedio = (ultimos_cota["cota_mazar"].iloc[-1] - ultimos_cota["cota_mazar"].iloc[0]) / (len(ultimos_cota) - 1)
else:
    cambio_diario_promedio = 0

cota_hoy = tabla_cota["cota_mazar"].iloc[-1]
prediccion_cota_manana = round(cota_hoy + cambio_diario_promedio, 2)

ultimos_demanda = tabla_demanda.tail(5)
prediccion_demanda_manana = round(ultimos_demanda["pico_demanda_mw"].mean(), 1)

fecha_prediccion_objetivo = hoy.strftime("%Y-%m-%d")  # "hoy" será el "mañana" cuando se cumpla

nueva_prediccion = pd.DataFrame([{
    "fecha_objetivo": fecha_prediccion_objetivo,
    "cota_predicha": prediccion_cota_manana,
    "demanda_predicha": prediccion_demanda_manana,
    "cota_real": None,
    "demanda_real": None,
    "error_cota": None,
    "error_demanda": None
}])

if os.path.exists(archivo_predicciones):
    tabla_pred = pd.read_csv(archivo_predicciones)
else:
    tabla_pred = pd.DataFrame(columns=nueva_prediccion.columns)

# Evitar duplicar predicción del mismo día objetivo
if fecha_prediccion_objetivo not in tabla_pred["fecha_objetivo"].astype(str).values:
    tabla_pred = pd.concat([tabla_pred, nueva_prediccion], ignore_index=True)
    print(f"🔮 Predicción para {fecha_prediccion_objetivo}: cota={prediccion_cota_manana}, demanda={prediccion_demanda_manana}")

# ---------- 6. RELLENAR PREDICCIONES ANTERIORES CON EL DATO REAL ----------
mask_pendiente = tabla_pred["fecha_objetivo"] == fecha_dato  # "fecha_dato" es el día que ya se cerró (ayer)
if mask_pendiente.any():
    fila_real_cota = tabla_cota[tabla_cota["fecha"] == fecha_dato]
    fila_real_demanda = tabla_demanda[tabla_demanda["fecha"] == fecha_dato]

    if not fila_real_cota.empty:
        real_cota = fila_real_cota["cota_mazar"].iloc[0]
        tabla_pred.loc[mask_pendiente, "cota_real"] = real_cota
        tabla_pred.loc[mask_pendiente, "error_cota"] = round(real_cota - tabla_pred.loc[mask_pendiente, "cota_predicha"].iloc[0], 2)

    if not fila_real_demanda.empty:
        real_demanda = fila_real_demanda["pico_demanda_mw"].iloc[0]
        tabla_pred.loc[mask_pendiente, "demanda_real"] = real_demanda
        tabla_pred.loc[mask_pendiente, "error_demanda"] = round(real_demanda - tabla_pred.loc[mask_pendiente, "demanda_predicha"].iloc[0], 1)

    print(f"✅ Comparación completada para {fecha_dato}")

tabla_pred.to_csv(archivo_predicciones, index=False)
print("\n--- Predicciones (últimas 5) ---")
print(tabla_pred.tail())
