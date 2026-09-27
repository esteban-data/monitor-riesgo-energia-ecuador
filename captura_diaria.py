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
