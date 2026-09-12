"""Medición que refutó el ADR-0027 (enrutado por similitud vectorial).

Reproduce el experimento: 7 consultas (5 sinónimos con respuesta conocida + 2
fuera de alcance) contra las 4 descripciones del catálogo real de `tools.py`.

    ollama pull nomic-embed-text
    python adr0027_medicion_embeddings.py nomic-embed-text mxbai-embed-large paraphrase-multilingual

Resultado (2026-08-05): ningún modelo superó 3/5 aciertos, y la consulta del
escenario 2 de la consigna falla en los tres. En dos de ellos los rangos de score
se solapan — no existe umbral que separe aciertos de fallos.

Ver `docs/adr/0027-rag-similitud-enrutado-consultas.md` (status: rejected).
"""
import json, urllib.request, math, sys
sys.stdout.reconfigure(encoding='utf-8')

def embed(modelo, texto):
    req = urllib.request.Request('http://localhost:11434/api/embed',
        data=json.dumps({'model': modelo, 'input': texto}).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())['embeddings'][0]

def coseno(a, b):
    n = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return n/(na*nb) if na and nb else 0.0

H = {
 'CROMOSOMAS_PARA_REVISION': 'Lista los cromosomas marcados en naranja: los que el modelo de IA clasifico con confianza por debajo del umbral y que el analista todavia no resolvio. Para preguntas sobre que cromosomas requieren atencion, revision manual o tienen baja confianza.',
 'CASOS_PENDIENTES_FIRMA': 'Lista los casos que el analista ya valido y esperan la firma digital del Supervisor. Para preguntas sobre que casos estan esperando al supervisor o pendientes de firma.',
 'CASOS_REPORTADOS': 'Lista los casos cerrados, con su nomenclatura ISCN ya emitida. Para preguntas sobre casos terminados, reportados o con ISCN.',
 'CASOS_EN_PROCESO': 'Lista las muestras que el pipeline de IA todavia esta procesando. Para preguntas sobre que muestras estan en proceso o en cola.',
}
P = [
 ('esc.2 SINONIMO', '¿Cuales necesitan que el analista los mire de nuevo?', 'CROMOSOMAS_PARA_REVISION'),
 ('sinonimo 2', '¿Que cromosomas son dudosos?', 'CROMOSOMAS_PARA_REVISION'),
 ('sinonimo 3', '¿Quien tiene que aprobar los casos listos?', 'CASOS_PENDIENTES_FIRMA'),
 ('sinonimo 4', '¿Que analisis ya terminaron?', 'CASOS_REPORTADOS'),
 ('sinonimo 5', '¿Que muestras siguen en la cola de la maquina?', 'CASOS_EN_PROCESO'),
 ('esc.3 FUERA', '¿Cual es el presupuesto del laboratorio para 2027?', None),
 ('fuera 2', '¿Cuantos empleados tiene el hospital?', None),
]

for modelo in sys.argv[1:]:
    try:
        vecs = {n: embed(modelo, d) for n, d in H.items()}
    except Exception as e:
        print(f'\n### {modelo}: NO disponible ({type(e).__name__})'); continue
    print(f'\n### {modelo}  (dim {len(next(iter(vecs.values())))})')
    aciertos=0; total=0; s_ok=[]; s_mal=[]; s_fuera=[]
    for etq, preg, esp in P:
        v = embed(modelo, preg)
        rank = sorted(((coseno(v, vh), n) for n, vh in vecs.items()), reverse=True)
        score, eleg = rank[0]
        if esp is None:
            s_fuera.append(score); estado='(fuera)'
        else:
            total+=1
            if eleg==esp: aciertos+=1; s_ok.append(score); estado='OK'
            else: s_mal.append(score); estado='FALLA'
        print(f'  {etq:16} -> {eleg:26} {score:.3f}  {estado}')
    print(f'  aciertos: {aciertos}/{total}')
    if s_ok and s_mal:
        print(f'  acierto min {min(s_ok):.3f} | fallo max {max(s_mal):.3f} -> '
              f'{"SEPARA" if min(s_ok)>max(s_mal) else "SE SOLAPA"}')
    elif s_ok:
        print(f'  acierto min {min(s_ok):.3f} | sin fallos')
    if s_ok and s_fuera:
        print(f'  acierto min {min(s_ok):.3f} | fuera max {max(s_fuera):.3f} -> '
              f'{"SEPARA" if min(s_ok)>max(s_fuera) else "SE SOLAPA"}')
