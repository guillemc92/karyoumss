/**
 * ToolQueryPage — consultas en lenguaje natural (Módulo 6, tool calling).
 *
 * La consigna exige que en pantalla se vea **qué herramienta se usó y de qué
 * tabla salió el dato**. Esta página existe para eso: no es un chat, es una
 * consola de consultas con procedencia visible.
 *
 * Lo que se muestra en cada respuesta:
 *
 *   camino  KEYWORD (sin modelo) · LLM (el modelo eligió) · SIN_MATCH
 *   tool    la herramienta ejecutada
 *   source  la tabla real de la que salieron las filas
 *
 * Sin esa evidencia, un usuario no puede distinguir un dato consultado de uno
 * inventado — que es justamente lo que esta arquitectura hace imposible.
 *
 * Los ejemplos precargados son los cuatro escenarios de la consigna, para poder
 * demostrarlos sin escribir a mano.
 */
import { useState } from 'react';
import { BiomedShell } from '../components/BiomedShell';
import { useToolCatalogo, useToolQuery } from '../hooks/useToolQuery';
import { CAMINO_LABEL, type CaminoConsulta, type ToolRespuesta } from '../types/tools';

/** Los escenarios de la consigna: misma pregunta de fondo en 1, 2 y 4. */
const EJEMPLOS: { etiqueta: string; pregunta: string; nota: string }[] = [
  {
    etiqueta: '1. Controlado',
    pregunta: '¿Qué cromosomas están naranjas?',
    nota: 'Usa una palabra del catálogo → se resuelve sin llamar al modelo.',
  },
  {
    etiqueta: '2. Sinónimo',
    pregunta: '¿Cuáles necesitan que el analista los mire de nuevo?',
    nota: 'El dato existe pero la palabra no está en el catálogo → escala al modelo. Debe devolver lo mismo que el 1.',
  },
  {
    etiqueta: '3. Fuera de alcance',
    pregunta: '¿Cuál es el presupuesto del laboratorio para 2027?',
    nota: 'Ninguna herramienta responde eso → dice que no sabe. No es un error.',
  },
];

const CAMINO_CLASE: Record<CaminoConsulta, string> = {
  KEYWORD: 'tool-badge--keyword',
  LLM: 'tool-badge--llm',
  SIN_MATCH: 'tool-badge--sinmatch',
};

function Procedencia({ r }: { r: ToolRespuesta }) {
  return (
    <div className="tool-procedencia" data-testid="tool-procedencia">
      <span className={`tool-badge ${CAMINO_CLASE[r.camino]}`} data-testid="tool-camino">
        {CAMINO_LABEL[r.camino]}
      </span>
      {r.tool && (
        <span className="tool-meta" data-testid="tool-nombre">
          Herramienta: <code>{r.tool}</code>
        </span>
      )}
      {r.source && (
        <span className="tool-meta" data-testid="tool-fuente">
          Fuente: <code>{r.source}</code>
        </span>
      )}
      <span className="tool-meta" data-testid="tool-latencia">{r.latency_ms} ms</span>
    </div>
  );
}

function TablaFilas({ filas }: { filas: Record<string, string>[] }) {
  if (filas.length === 0) return null;
  const columnas = Object.keys(filas[0]);

  return (
    <div className="tool-tabla-wrap">
      <table className="tool-tabla" data-testid="tool-tabla">
        <thead>
          <tr>{columnas.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {filas.map((fila, i) => (
            <tr key={i} data-testid="tool-fila">
              {columnas.map((c) => <td key={c}>{fila[c]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Resultado({ r }: { r: ToolRespuesta }) {
  return (
    <section className="tool-resultado" data-testid="tool-resultado">
      <Procedencia r={r} />

      {r.motivo && (
        <p className="tool-motivo" data-testid="tool-motivo">
          <strong>Por qué el modelo eligió esta herramienta:</strong> {r.motivo}
        </p>
      )}

      <p className="tool-mensaje" data-testid="tool-mensaje">{r.mensaje}</p>

      <TablaFilas filas={r.filas} />

      {/* SIN_MATCH: decir "no sé" sin decir qué sí se sabe deja al usuario sin salida. */}
      {r.catalogo && (
        <div className="tool-catalogo" data-testid="tool-catalogo-fallback">
          <strong>Lo que sí puedo responder:</strong>
          <ul>
            {r.catalogo.map((h) => (
              <li key={h.herramienta}>
                <code>{h.herramienta}</code> — {h.responde}
                <span className="tool-fuente-tag">{h.fuente}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function ToolQueryPage() {
  const [pregunta, setPregunta] = useState('');
  const consulta = useToolQuery();
  const { data: catalogo } = useToolCatalogo();

  function preguntar(texto: string) {
    const limpia = texto.trim();
    if (!limpia || consulta.isPending) return;
    setPregunta(limpia);
    consulta.mutate(limpia);
  }

  return (
    <BiomedShell>
      <div className="page-header">
        <div>
          <h1><i className="fas fa-comments"></i> Consultas al sistema</h1>
          <p>El modelo elige la herramienta; los datos los produce el código</p>
        </div>
      </div>

      <form
        className="tool-form"
        onSubmit={(e) => { e.preventDefault(); preguntar(pregunta); }}
      >
        <input
          type="text"
          value={pregunta}
          onChange={(e) => setPregunta(e.target.value)}
          placeholder="Ej.: ¿Qué cromosomas están naranjas?"
          aria-label="Consulta en lenguaje natural"
          data-testid="tool-input"
        />
        <button
          type="submit" className="btn-primary"
          disabled={consulta.isPending || !pregunta.trim()}
          data-testid="tool-submit"
        >
          {consulta.isPending ? 'Consultando…' : 'Consultar'}
        </button>
      </form>

      <div className="tool-ejemplos" data-testid="tool-ejemplos">
        <span className="tool-ejemplos__label">Escenarios de prueba:</span>
        {EJEMPLOS.map((e) => (
          <button
            key={e.etiqueta}
            type="button" className="btn-outline"
            onClick={() => preguntar(e.pregunta)}
            disabled={consulta.isPending}
            title={e.nota}
            data-testid={`tool-ejemplo-${e.etiqueta[0]}`}
          >{e.etiqueta}</button>
        ))}
      </div>

      {consulta.isPending && (
        <p className="tool-cargando" role="status" data-testid="tool-cargando">
          Resolviendo… si la consulta necesita al modelo puede tardar 1-2 minutos
          (CPU sin GPU).
        </p>
      )}

      {consulta.isError && (
        <p role="alert" data-testid="tool-error">
          No se pudo completar la consulta. Intente nuevamente.
        </p>
      )}

      {consulta.data && <Resultado r={consulta.data} />}

      {/* El catálogo siempre visible: el usuario sabe qué puede preguntar
          antes de escribir, no solo cuando falla. */}
      {!consulta.data && catalogo && (
        <section className="tool-catalogo" data-testid="tool-catalogo">
          <strong>Este sistema puede responder:</strong>
          <ul>
            {catalogo.herramientas.map((h) => (
              <li key={h.herramienta}>
                <code>{h.herramienta}</code> — {h.responde}
                <span className="tool-fuente-tag">{h.fuente}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </BiomedShell>
  );
}
