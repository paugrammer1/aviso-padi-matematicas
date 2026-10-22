
import os
import json
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

URL_PADI = (
    "https://gestiona7.madrid.org/nsus_rest_ares/v1/"
    "ActosPublicosSustituciones/consultaNecesidades"
)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


hoy = datetime.now(ZoneInfo("Europe/Madrid"))
# Siguiente día entre lunes y viernes
dia_asignacion = hoy + timedelta(days=1)
while dia_asignacion.weekday() >= 5:
    dia_asignacion += timedelta(days=1)
fecha = dia_asignacion.strftime("%Y-%m-%d")
fecha_visible = dia_asignacion.strftime("%d/%m/%Y")

filtros = {
    "fcpublico": fecha,
    "cfunc": "0590006",
    "coddat": "T",
    "itperfilacto": "E"
}

peticion = urllib.request.Request(
    URL_PADI,
    data=json.dumps(filtros).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json"
    },
    method="POST"
)

with urllib.request.urlopen(peticion, timeout=30) as respuesta:
    plazas = json.load(respuesta)

with open("plazas.json", "w", encoding="utf-8") as archivo:
    json.dump(plazas, archivo, ensure_ascii=False, indent=2)

if not isinstance(plazas, list):
    raise ValueError("Respuesta inesperada de PADI")


def valor(plaza, campo):
    return str(plaza.get(campo) or "").strip()


def fecha_es(fecha_iso):
    if not fecha_iso:
        return "No indicada"
    try:
        return datetime.strptime(
            fecha_iso[:10], "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
    except ValueError:
        return fecha_iso


def ficha(plaza, numero):
    centro = valor(plaza, "centro") or "Centro no indicado"
    localidad = valor(plaza, "localidad") or "Sin localidad"
    dat = valor(plaza, "dat") or "Sin DAT"

    jornada = (
        valor(plaza, "dtipopuesto")
        or valor(plaza, "dtpvacante")
        or valor(plaza, "tipopuesto")
        or "No indicada"
    )

    tipo = (
        valor(plaza, "dsustitucion")
        or valor(plaza, "tipopuesto")
        or "No indicado"
    )

    causa = valor(plaza, "causa") or "No indicada"
    fin = fecha_es(valor(plaza, "fhasta"))
    observaciones = valor(plaza, "observaciones")
    identificador = valor(plaza, "idnsustituciones")

    lineas = [
        f"🏫 {numero}. {centro}",
        f"📍 {localidad} · DAT {dat}",
        f"🕒 Jornada: {jornada}",
        f"📋 Tipo: {tipo}",
        f"🩺 Causa: {causa}",
        f"📅 Fin estimado: {fin}"
    ]

    if observaciones:
        lineas.append(f"📝 {observaciones}")

    if identificador:
        lineas.append(f"🔎 ID: {identificador}")

    return "\n".join(lineas)


def enviar_telegram(texto):
    datos = json.dumps({
        "chat_id": CHAT_ID,
        "text": texto
    }).encode("utf-8")

    peticion = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=datos,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        resultado = json.load(respuesta)

    if not resultado.get("ok"):
        raise RuntimeError("Error al enviar a Telegram")


cabecera = (
    f"📚 PADI MATEMÁTICAS\n"
    f"📅 {fecha_visible}\n"
    f"📊 Total: {len(plazas)} plazas\n"
    f"📍 Todas las DAT"
)

if not plazas:
    enviar_telegram(
        cabecera + "\n\nNo hay plazas en esta consulta."
    )
else:
    # Telegram admite hasta 4096 caracteres por mensaje.
    # Agrupamos fichas completas sin cortarlas por la mitad.
    mensaje = cabecera

    for numero, plaza in enumerate(plazas, 1):
        bloque = "\n\n━━━━━━━━━━━━━━\n\n" + ficha(
            plaza, numero
        )

        if len(mensaje) + len(bloque) > 3500:
            enviar_telegram(mensaje)
            mensaje = (
                f"📚 PADI MATEMÁTICAS · Continuación\n"
                f"📅 {fecha_visible}"
            )

        mensaje += bloque

    enviar_telegram(mensaje)

print(f"Enviadas {len(plazas)} plazas a Telegram")
