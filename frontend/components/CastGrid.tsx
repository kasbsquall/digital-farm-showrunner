"use client";

import { useState } from "react";
import { type Character, type Episode, ossThumb } from "@/lib/api";

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

export function CastGrid({
  characters,
  episodes,
}: {
  characters: Character[];
  episodes: Episode[];
}) {
  const [sel, setSel] = useState<Character | null>(null);

  const epsOf = (name: string) =>
    episodes.filter((e) => (e.characters_used ?? []).includes(name));

  return (
    <>
      <div className="cast-grid">
        {characters.map((c) => {
          const n = epsOf(c.name).length;
          return (
            <button className="cast-card" key={c.name} onClick={() => setSel(c)}>
              <div className="pic">
                {c.image_url && <img src={ossThumb(c.image_url, 500)} alt={c.name} />}
                {n > 0 && (
                  <span className="count">★ {n} {n === 1 ? "ep" : "eps"}</span>
                )}
              </div>
              <div className="info">
                <b>{c.name}</b>
                <div className="role">{ROLE[c.species] ?? c.species}</div>
                <p>{c.personality}</p>
              </div>
            </button>
          );
        })}
      </div>

      {sel && (
        <div className="modal-scrim" onClick={() => setSel(null)}>
          <div className="modal char-modal" role="dialog" aria-modal="true" aria-label={sel.name} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <span className="eyebrow">Cast member</span>
              </div>
              <button className="modal-x" onClick={() => setSel(null)} aria-label="Close">✕</button>
            </div>
            <div className="char-hero">
              {sel.image_url && <img src={ossThumb(sel.image_url, 400)} alt={sel.name} />}
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
    </>
  );
}
