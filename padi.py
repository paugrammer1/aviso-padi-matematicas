
import os
import json
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

URL_PADI = (
    "https://gestiona7.madrid.org/nsus_rest_ares/v1/"
    "ActosPublicosSustituciones/consultaNecesidades"
)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

hoy = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")

filtros = {
    "fcpublico": hoy,
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

if not isinstance(plazas, list):
    raise ValueError("PADI no ha devuelto una lista de plazas")

if not plazas:
    mensaje = f"📚 PADI Matemáticas — {hoy}\n\nNo hay plazas en la consulta."
else:
    mensaje = (
        f"📚 PADI Matemáticas — {hoy}\n"
        f"Total: {len(plazas)} plazas\n\n"
        + json.dumps(plazas, ensure_ascii=False, indent=2)
    )

# Telegram limita el tamaño de cada mensaje.
# Dividimos el resultado sin eliminar plazas.
for inicio in range(0, len(mensaje), 3500):
    fragmento = mensaje[inicio:inicio + 3500]
    datos = json.dumps({
        "chat_id": CHAT_ID,
        "text": fragmento
    }).encode("utf-8")

    envio = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=datos,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(envio, timeout=30) as respuesta:
        resultado = json.load(respuesta)
        if not resultado.get("ok"):
            raise RuntimeError("Telegram no ha aceptado el mensaje")

print(f"Consulta completada: {len(plazas)} plazas")
