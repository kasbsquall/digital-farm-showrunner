"use client";

import { useRef, useState } from "react";
import { streamEpisode } from "@/lib/api";

type Status = "idle" | "active" | "done" | "reject";

const STAGES = [
  { key: "scriptwriter", role: "Guionista", tag: "qwen3.7 · texto" },
  { key: "director", role: "Director de Producción", tag: "qwen3.7 · keyframe" },
  { key: "video", role: "Keyframe → Video → Visión", tag: "qwen-image · happyhorse-i2v · qwen3-vl" },
  { key: "qa", role: "Control de Calidad", tag: "qwen3.7 · texto" },
  { key: "packager", role: "Empaquetador", tag: "qwen3.7 · publicación" },
] as const;

type Data = {
  script?: { event: string; script: string };
  director?: { keyframe_prompt: string; motion_prompt: string; video_tool: string };
  video?: { video_url: string; video_description: string };
  qa?: { qa_status: string; qa_notes: string };
  pack?: { title: string; description: string; thumbnail_url: string };
};

export function Studio({ onDone }: { onDone: () => void }) {
  const [idea, setIdea] = useState("");
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<Record<string, Status>>({});
  const [data, setData] = useState<Data>({});
  const [regen, setRegen] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const finished = useRef(false);

  function setStage(key: string, s: Status) {
    setStatus((prev) => ({ ...prev, [key]: s }));
  }

  function start() {
    setRunning(true);
    setError(null);
    setRegen(0);
    setData({});
    setStatus({ scriptwriter: "active" });
    finished.current = false;

    const es = streamEpisode(idea);
    esRef.current = es;

    es.addEventListener("scriptwriter", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      setData((p) => ({ ...p, script: d.story }));
      setStage("scriptwriter", "done");
      setStage("director", "active");
    });
    es.addEventListener("director", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      setData((p) => ({ ...p, director: d.direction }));
      setStage("director", "done");
      setStage("video", "active");
    });
    es.addEventListener("video", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      setData((p) => ({ ...p, video: d }));
      setStage("video", "done");
      setStage("qa", "active");
    });
    es.addEventListener("qa", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      const approved = d.qa?.qa_status === "approved";
      setData((p) => ({ ...p, qa: d.qa }));
      setStage("qa", approved ? "done" : "reject");
      if (approved) {
        setStage("packager", "active");
      } else {
        setRegen((r) => r + 1);
        setStage("director", "active"); // regen loop
      }
    });
    es.addEventListener("packager", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      setData((p) => ({ ...p, pack: { ...d.pack, thumbnail_url: d.thumbnail_url } }));
      setStage("qa", "done");
      setStage("packager", "done");
    });
    es.addEventListener("done", () => {
      finished.current = true;
      es.close();
      setRunning(false);
      onDone();
    });
    es.addEventListener("failed", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      finished.current = true;
      es.close();
      setRunning(false);
      setError(d.message ?? "Falló la generación");
    });
    es.onerror = () => {
      if (finished.current) return;
      es.close();
      setRunning(false);
      setError("Se perdió la conexión con el estudio (¿backend activo?).");
    };
  }

  return (
    <section className="studio">
      <div className="panel">
        <h2>El Estudio</h2>
        <p className="hint">Escribe una idea o déjalo en blanco y deja que los agentes improvisen.</p>
        <div className="field">
          <label>Idea del episodio (opcional)</label>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Ej: Bruno organiza una huelga contra el amanecer…"
            disabled={running}
          />
        </div>
        <button className="btn" onClick={start} disabled={running}>
          {running ? "● Rodando en vivo…" : "🎬 Producir episodio"}
        </button>
        {error && <p className="err">⚠ {error}</p>}
      </div>

      <div className="wizard">
        {STAGES.map((st, i) => {
          const s = status[st.key] ?? "idle";
          return (
            <div className="stage" key={st.key} data-state={s} data-n={i + 1}>
              <div className="role">
                {st.role} <span className="tag">{st.tag}</span>
              </div>
              <StageBody k={st.key} data={data} regen={regen} />
            </div>
          );
        })}
      </div>
    </section>
  );
}

function StageBody({ k, data, regen }: { k: string; data: Data; regen: number }) {
  if (k === "scriptwriter" && data.script)
    return (
      <div className="out">
        <span className="k">Evento</span>
        {data.script.event}
        <span className="k">Guion</span>
        {data.script.script}
      </div>
    );
  if (k === "director" && data.director)
    return (
      <div className="out">
        <span className="k">Keyframe (imagen semilla)</span>
        {data.director.keyframe_prompt}
        <span className="k">Acción de 5s</span>
        {data.director.motion_prompt}
        {regen > 0 && <div className="regen">↻ regeneración #{regen}</div>}
      </div>
    );
  if (k === "video" && data.video)
    return (
      <div className="out">
        <span className="k">Lo que la IA ve en el video</span>
        {data.video.video_description || "(video en modo demo)"}
        {data.video.video_url && (
          <video className="wizard-video" src={data.video.video_url} controls preload="metadata" />
        )}
      </div>
    );
  if (k === "qa" && data.qa)
    return (
      <div className="out">
        <span className="k">Veredicto</span>
        {data.qa.qa_status === "approved" ? "✓ Aprobado" : "✗ Rechazado"} — {data.qa.qa_notes}
      </div>
    );
  if (k === "packager" && data.pack)
    return (
      <div className="out">
        <span className="k">Título</span>
        {data.pack.title}
        {data.pack.thumbnail_url && (
          <img
            src={data.pack.thumbnail_url}
            alt="thumbnail"
            style={{ width: "100%", borderRadius: 10, marginTop: 8, border: "1px solid var(--line)" }}
          />
        )}
      </div>
    );
  return null;
}
