"use client";

import { useEffect, useState } from "react";
import { API, Character, Episode, getCharacters, getEpisodes } from "@/lib/api";
import { CinemaFeed } from "@/components/CinemaFeed";
import { CastGrid } from "@/components/CastGrid";
import { Studio } from "@/components/Studio";

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
          <img src="/logo.png" alt="MUCKFLIX" />
          <div className="word">
            MUCK<b>FLIX</b>
            <small>The Digital Farm Showrunner</small>
          </div>
        </div>
        <span className="pill">
          <span className="dot" /> 4 AI agents · fully autonomous
        </span>
      </div>

      <header className="hero">
        <div className="bg" style={{ backgroundImage: "url(/hero.png)" }} />
        <div className="inner">
          <span className="eyebrow">Qwen Cloud · AI Showrunner</span>
          <h1>
            A claymation farm drama,<br />
            <span className="em">every single day</span>.
          </h1>
          <p>
            Four AI agents invent the story, paint the scene, film it, check what really
            happened on screen, and publish the episode. No human writers on set.
          </p>
        </div>
      </header>

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">Live</span>
            <h2>The Studio</h2>
          </div>
        </div>
        <Studio onDone={refresh} />
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">Now showing</span>
            <h2>Fresh from the barn</h2>
          </div>
          <span className="count">{episodes.length} episodes</span>
        </div>
        {error && <p className="err">⚠ {error}</p>}
        <CinemaFeed episodes={episodes} chars={charMap} />
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">Cast</span>
            <h2>Meet the barnyard</h2>
          </div>
        </div>
        <CastGrid characters={characters} />
      </section>

      <footer>
        MUCKFLIX · The Digital Farm Showrunner · Qwen Cloud Hackathon 2026 · Kevin Soto Burgos · AVANC3
      </footer>
    </div>
  );
}
