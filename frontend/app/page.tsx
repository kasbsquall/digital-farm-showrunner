"use client";

import { useEffect, useState } from "react";
import { API, Episode, getEpisodes, generateEpisode } from "@/lib/api";
import { PipelineStepper } from "@/components/PipelineStepper";
import { EpisodeCard } from "@/components/EpisodeCard";

const CAST = [
  { emoji: "🐔", name: "Bruno" },
  { emoji: "🐄", name: "Lola" },
  { emoji: "🚜", name: "Tractor" },
  { emoji: "🐖", name: "Pepe" },
  { emoji: "🐤", name: "Nina" },
];

const STAGE_MS = 900; // visual pacing per agent while the request runs

export default function Home() {
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [current, setCurrent] = useState(-1);
  const [regens, setRegens] = useState(0);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEpisodes().then(setEpisodes).catch(() => setError("Backend no disponible en " + API));
  }, []);

  async function handleGenerate() {
    setRunning(true);
    setError(null);
    setRegens(0);
    setCurrent(0);

    // Animate the 4 stages while the real pipeline runs on the backend.
    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 1; i < 4; i++) {
      timers.push(setTimeout(() => setCurrent(i), STAGE_MS * i));
    }

    try {
      const ep = await generateEpisode();
      timers.forEach(clearTimeout);
      setCurrent(4);
      setRegens(Math.max(0, (ep.qa_attempts ?? 1) - 1));
      const fresh = await getEpisodes();
      setEpisodes(fresh);
    } catch (e) {
      setError((e as Error).message);
      setCurrent(-1);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="shell">
      <header className="masthead">
        <div>
          <div className="kicker">Qwen Cloud · Track 2 · AI Showrunner</div>
          <h1>The Digital Farm</h1>
        </div>
        <div className="dateline">
          Edición diaria
          <br />
          generada por IA
        </div>
      </header>

      <p className="hero-tag">
        Cada día, cuatro agentes autónomos inventan, dirigen, revisan y publican un
        micro-drama absurdo del corral. Sin guionistas humanos.
      </p>

      <div className="cast">
        {CAST.map((c) => (
          <span className="chip" key={c.name}>
            <span aria-hidden>{c.emoji}</span> {c.name}
          </span>
        ))}
      </div>

      <section className="studio" style={{ marginTop: "1.5rem" }}>
        <PipelineStepper current={current} regens={regens} />
        <div className="panel">
          <h2>Producir episodio de hoy</h2>
          <p className="sub">Dispara el pipeline completo con un clic</p>
          <button className="btn" onClick={handleGenerate} disabled={running}>
            {running ? "Rodando…" : "🎬 Generar episodio"}
          </button>
          {error && (
            <p style={{ color: "var(--barn-deep)", marginTop: "1rem", fontSize: "0.85rem" }}>
              ⚠ {error}
            </p>
          )}
          {current === 4 && !running && (
            <p style={{ color: "var(--meadow)", marginTop: "1rem", fontWeight: 700 }}>
              ✓ Episodio listo y publicado en el feed
            </p>
          )}
        </div>
      </section>

      <section>
        <div className="feed-head">
          <h2>El feed del corral</h2>
          <span className="count">{episodes.length} episodios</span>
        </div>
        {episodes.length === 0 ? (
          <p className="empty">Aún no hay episodios. Pulsa “Generar episodio”.</p>
        ) : (
          <div className="grid">
            {episodes.map((ep) => (
              <EpisodeCard key={ep.id} ep={ep} />
            ))}
          </div>
        )}
      </section>

      <footer>
        The Digital Farm Showrunner · Qwen Cloud Hackathon 2026 · Kevin Soto Burgos · AVANC3
      </footer>
    </div>
  );
}
