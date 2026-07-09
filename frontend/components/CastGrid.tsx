"use client";

import { useState } from "react";
import { type Character, type Episode, ossThumb, createCharacter } from "@/lib/api";

const ROLE: Record<string, string> = {
  rooster: "The union leader",
  cow: "The romantic",
  pig: "The philosopher",
  hen: "The reporter",
  goat: "The troublemaker",
  duck: "The drama queen",
  sheep: "The overthinker",
  donkey: "The pessimist",
  goose: "The bouncer",
};

const EMOJI: Record<string, string> = {
  rooster: "🐔", cow: "🐄", pig: "🐖", hen: "🐤", goat: "🐐",
  duck: "🦆", sheep: "🐑", donkey: "🫏", goose: "🪿",
};

export function CastGrid({
  characters,
  episodes,
  onCreated,
}: {
  characters: Character[];
  episodes: Episode[];
  onCreated: () => void;
}) {
  const [sel, setSel] = useState<Character | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", species: "", personality: "", look: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const epsOf = (name: string) => episodes.filter((e) => (e.characters_used ?? []).includes(name));

  async function submit() {
    if (!form.name.trim() || !form.personality.trim()) {
      setErr("Give your character at least a name and a personality.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await createCharacter(form);
      setCreating(false);
      setForm({ name: "", species: "", personality: "", look: "" });
      onCreated();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="cast-grid">
        {characters.map((c) => {
          const n = epsOf(c.name).length;
          return (
            <button className="cast-card" key={c.name} onClick={() => setSel(c)}>
              <div className="pic">
                {c.image_url ? (
                  <img src={ossThumb(c.image_url, 500)} alt={c.name} />
                ) : (
                  <span className="pic-emoji">{EMOJI[c.species] ?? "🎭"}</span>
                )}
                {n > 0 && <span className="count">★ {n} {n === 1 ? "ep" : "eps"}</span>}
              </div>
              <div className="info">
                <b>{c.name}</b>
                <div className="role">{ROLE[c.species] ?? c.species}</div>
                <p>{c.personality}</p>
              </div>
            </button>
          );
        })}

        <button className="cast-card cast-add" onClick={() => setCreating(true)}>
          <div className="add-inner">
            <span className="plus">＋</span>
            <b>Create your own</b>
            <p>Add your character to the cast and cast it in an episode.</p>
          </div>
        </button>
      </div>

      {/* Character detail */}
      {sel && (
        <div className="modal-scrim" onClick={() => setSel(null)}>
          <div className="modal char-modal" role="dialog" aria-modal="true" aria-label={sel.name} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <span className="eyebrow">Cast member</span>
              <button className="modal-x" onClick={() => setSel(null)} aria-label="Close">✕</button>
            </div>
            <div className="char-hero">
              {sel.image_url ? (
                <img src={ossThumb(sel.image_url, 400)} alt={sel.name} />
              ) : (
                <span className="char-emoji">{EMOJI[sel.species] ?? "🎭"}</span>
              )}
              <div>
                <div className="role">{ROLE[sel.species] ?? sel.species}</div>
                <h3>{sel.name}</h3>
                <p>{sel.personality}</p>
              </div>
            </div>
            <div className="char-eps">
              <span className="lbl">Featured in</span>
              {epsOf(sel.name).length === 0 ? (
                <p className="none">No episodes yet — produce one and cast {sel.name}!</p>
              ) : (
                <div className="row">
                  {epsOf(sel.name).map((e) => (
                    <div className="ep" key={e.id}>
                      <img src={ossThumb(e.thumbnail_url, 300)} alt="" />
                      <span>{e.title ?? e.event}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create character */}
      {creating && (
        <div className="modal-scrim" onClick={() => !busy && setCreating(false)}>
          <div className="modal char-modal" role="dialog" aria-modal="true" aria-label="Create character" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <span className="eyebrow">New cast member</span>
                <h3>Create your own character</h3>
              </div>
              <button className="modal-x" onClick={() => setCreating(false)} aria-label="Close" disabled={busy}>✕</button>
            </div>
            <div className="create-form">
              <div className="field">
                <label htmlFor="cc-name">Name</label>
                <input id="cc-name" className="text-input" value={form.name} maxLength={32}
                  onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Waldo" disabled={busy} />
              </div>
              <div className="field">
                <label htmlFor="cc-species">Animal / type</label>
                <input id="cc-species" className="text-input" value={form.species} maxLength={32}
                  onChange={(e) => setForm({ ...form, species: e.target.value })} placeholder="e.g. llama, turtle, robot chicken" disabled={busy} />
              </div>
              <div className="field">
                <label htmlFor="cc-pers">Personality</label>
                <textarea id="cc-pers" value={form.personality} maxLength={400}
                  onChange={(e) => setForm({ ...form, personality: e.target.value })} placeholder="e.g. a paranoid llama who thinks the barn is bugged" disabled={busy} />
              </div>
              <div className="field">
                <label htmlFor="cc-look">Look (optional)</label>
                <input id="cc-look" className="text-input" value={form.look} maxLength={200}
                  onChange={(e) => setForm({ ...form, look: e.target.value })} placeholder="e.g. fluffy cream llama with a tiny tinfoil hat" disabled={busy} />
              </div>
              {err && <p className="err">⚠ {err}</p>}
              <button className="btn" onClick={submit} disabled={busy}>
                <span>{busy ? "Sculpting in clay…" : "Add to the cast"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
