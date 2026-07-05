"use client";

import { useEffect, useState } from "react";
import { API, Character, Episode, getCharacters, getEpisodes } from "@/lib/api";
import { CharacterRail } from "@/components/CharacterRail";
import { Studio } from "@/components/Studio";
import { EpisodeCard } from "@/components/EpisodeCard";

export default function Home() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const [c, e] = await Promise.all([getCharacters(), getEpisodes()]);
      setCharacters(c);
      setEpisodes(e);
    } catch {
      setError("Backend no disponible en " + API);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const charMap: Record<string, string | null> = Object.fromEntries(
    characters.map((c) => [c.name, c.image_url])
  );

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <div className="logo">🐔</div>
          <div className="name">
            The Digital Farm
            <small>Qwen Cloud · AI Showrunner</small>
          </div>
        </div>
        <span className="pill">
          <span className="dot" /> pipeline de 4 agentes · autónomo
        </span>
      </div>

      <header className="hero">
        <h1>
          Dramas de granja<br />
          escritos, dirigidos y <span className="em">filmados</span> por IA.
        </h1>
        <p>
          Cuatro agentes autónomos inventan la historia, generan el video, revisan lo que
          realmente se ve en pantalla y publican el episodio. Sin humanos en el set.
        </p>
        <CharacterRail characters={characters} />
      </header>

      <Studio onDone={refresh} />

      <section>
        <div className="feed-head">
          <h2>El feed del corral</h2>
          <span className="count">{episodes.length} EPISODIOS</span>
        </div>
        {error && <p className="err">⚠ {error}</p>}
        {episodes.length === 0 ? (
          <p className="empty">// aún no hay episodios — produce el primero arriba</p>
        ) : (
          <div className="grid">
            {episodes.map((ep) => (
              <EpisodeCard key={ep.id} ep={ep} chars={charMap} />
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
