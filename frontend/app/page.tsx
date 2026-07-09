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
        <div className="inner">
          <span className="eyebrow">The autonomous AI content studio</span>
          <h1>
            Your own claymation show,<br />
            <span className="em">a new episode every day</span>.
          </h1>
          <p>
            Four AI agents write, film, quality-check and publish a brand-new claymation
            episode — with zero production team. Bring your own character and run your own
            daily show.
          </p>
        </div>
      </header>

      <section className="section">
        <div className="how">
          <div className="how-step">
            <span className="how-n">1</span>
            <b>Cast &amp; pitch</b>
            <p>Pick a character (or create your own) and toss in a one-line gag. Or just roll the dice.</p>
          </div>
          <div className="how-step">
            <span className="how-n">2</span>
            <b>4 agents produce it</b>
            <p>Writer → director → keyframe → image-to-video → a vision QA that watches the real clip and retakes if it misses.</p>
          </div>
          <div className="how-step">
            <span className="how-n">3</span>
            <b>A finished episode</b>
            <p>Title, thumbnail and a publish-ready video — consistent characters, every single day.</p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">Live</span>
            <h2>The Studio</h2>
          </div>
        </div>
        <div className="sec-scroll">
          <Studio onDone={refresh} characters={characters} />
        </div>
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
        <div className="sec-tex sec-crate">
          <CinemaFeed episodes={episodes} chars={charMap} />
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">Cast · bring your own</span>
            <h2>Meet the barnyard</h2>
          </div>
        </div>
        <CastGrid characters={characters} episodes={episodes} onCreated={refresh} />
      </section>

      <section className="section">
        <div className="impact">
          <h2>Daily video shouldn't need a studio</h2>
          <p>
            Consistent short-form video every day is the price of staying relevant online —
            and it's slow, expensive, and needs a team. MUCKFLIX turns one idea into a
            finished, on-brand, character-consistent episode for pennies, and lets your
            audience co-create the next one. The farm is our demo; the engine is the product.
          </p>
          <div className="who">
            <span>Creators</span>
            <span>Brand mascots</span>
            <span>Educators</span>
            <span>Kids' channels</span>
          </div>
        </div>
      </section>

      <footer>
        <div className="foot-card">
          <div className="foot-brand">
            <img src="/logo.png" alt="MUCKFLIX" />
            <div>
              <div className="word">MUCK<b>FLIX</b></div>
              <p>The world's first fully autonomous claymation farm channel. A brand-new
                micro-drama every day — written, filmed and edited by AI.</p>
            </div>
          </div>
          <div className="foot-stack">
            <div className="row">
              <span className="foot-chip">Qwen3.7</span>
              <span className="foot-chip">HappyHorse i2v</span>
              <span className="foot-chip">Qwen-Image</span>
              <span className="foot-chip">Qwen3-VL</span>
            </div>
            <div className="row">
              <span className="foot-chip">FastAPI</span>
              <span className="foot-chip">LangGraph</span>
              <span className="foot-chip">Next.js</span>
              <span className="foot-chip">Alibaba Cloud OSS</span>
            </div>
          </div>
        </div>
        <div className="foot-legal">
          Built by Kevin Soto Burgos · AVANC3 · Qwen Cloud Global AI Hackathon 2026 · Track 2: AI Showrunner
        </div>
      </footer>
    </div>
  );
}
