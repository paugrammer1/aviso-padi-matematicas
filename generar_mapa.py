import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from html import escape

ARCHIVO = Path('plazas.json')
SALIDA = Path('index.html')
CACHE = Path('coordenadas.json')

plazas = json.loads(ARCHIVO.read_text(encoding='utf-8'))
cache = json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {}
centros = {}
for p in plazas:
    clave = (str(p.get('ccentro') or ''), str(p.get('centro') or ''), str(p.get('localidad') or ''))
    centros.setdefault(clave, []).append(p)

marcadores = []
no_localizados = []
for (codigo, centro, localidad), ofertas in centros.items():
    clave = codigo or f'{centro}|{localidad}'
    if clave not in cache:
        consulta = f'{centro}, {localidad}, Comunidad de Madrid, España'
        url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': consulta, 'format': 'json', 'limit': 1, 'countrycodes': 'es'})
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'PADI-Matematicas-Mapa/1.0 (GitHub Actions; personal noncommercial project)'})
            with urllib.request.urlopen(req, timeout=20) as r:
                encontrados = json.load(r)
            cache[clave] = {'lat': float(encontrados[0]['lat']), 'lon': float(encontrados[0]['lon'])} if encontrados else None
        except Exception as e:
            print(f'No se pudo localizar {centro}: {e}')
            cache[clave] = None
        time.sleep(1.1)
    coords = cache[clave]
    if not coords:
        no_localizados.append(f'{centro} ({localidad})')
        continue
    descripciones = []
    for p in ofertas:
        jornada = p.get('dtipopuesto') or p.get('dtpvacante') or p.get('tipopuesto') or 'No indicada'
        descripciones.append({'jornada': jornada, 'tipo': p.get('dsustitucion') or '', 'causa': p.get('causa') or '', 'fin': p.get('fhasta') or '', 'observaciones': p.get('observaciones') or ''})
    marcadores.append({'centro': centro, 'localidad': localidad, 'dat': ofertas[0].get('dat') or '', 'lat': coords['lat'], 'lon': coords['lon'], 'plazas': descripciones})

CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
contenido = json.dumps(marcadores, ensure_ascii=False).replace('<', '\\u003c')
no_loc = json.dumps(no_localizados, ensure_ascii=False).replace('<', '\\u003c')
html = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mapa PADI Matemáticas</title><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"><style>body{margin:0;font-family:system-ui,Arial;background:#f8fafc;color:#172033}header{padding:15px 20px;background:#b91c1c;color:white}h1{font-size:1.25rem;margin:0}#map{height:72vh;min-height:380px}.info{padding:12px 20px}.leaflet-popup-content{max-height:240px;overflow:auto}small{color:#555}</style></head><body><header><h1>📍 PADI · Matemáticas</h1><div>Centros ofertados · Comunidad de Madrid</div></header><div id="map"></div><div class="info" id="resumen"></div><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>const centros=__DATOS__;const pendientes=__PENDIENTES__;const map=L.map('map').setView([40.42,-3.70],9);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19}).addTo(map);function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}const puntos=[];for(const c of centros){let detalles=c.plazas.map((p,i)=>'<p><b>Plaza '+(i+1)+'</b><br>Jornada: '+esc(p.jornada)+'<br>Tipo: '+esc(p.tipo)+'<br>Causa: '+esc(p.causa)+'<br>Fin estimado: '+esc(p.fin)+(p.observaciones?'<br>Observaciones: '+esc(p.observaciones):'')+'</p>').join('');let m=L.marker([c.lat,c.lon]).addTo(map).bindPopup('<b>'+esc(c.centro)+'</b><br>'+esc(c.localidad)+' · DAT '+esc(c.dat)+'<hr>'+detalles);puntos.push(m.getLatLng())}if(puntos.length)map.fitBounds(L.latLngBounds(puntos).pad(.15),{maxZoom:12});document.getElementById('resumen').textContent=centros.length+' centros localizados · '+centros.reduce((n,c)=>n+c.plazas.length,0)+' plazas en el mapa'+(pendientes.length?' · Sin ubicación verificada: '+pendientes.join('; '):'');</script></body></html>'''
SALIDA.write_text(html.replace('__DATOS__', contenido).replace('__PENDIENTES__', no_loc), encoding='utf-8')
print(f'Mapa generado: {len(marcadores)} centros; sin localizar: {len(no_localizados)}')
