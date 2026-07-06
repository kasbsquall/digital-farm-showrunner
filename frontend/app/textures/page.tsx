"use client";

const TEX = [
  { id: 1, key: "wood", label: "Red barn wood planks" },
  { id: 2, key: "hay", label: "Golden hay bales" },
  { id: 3, key: "clay", label: "Cream clay / plaster wall" },
  { id: 4, key: "burlap", label: "Brown burlap sack" },
  { id: 5, key: "cork", label: "Cork notice board" },
  { id: 6, key: "crate", label: "Wooden crate slats" },
];

export default function Textures() {
  return (
    <div className="shell" style={{ padding: "2rem 0 4rem" }}>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "2.4rem", margin: "0 0 0.3rem" }}>
        Texture picker
      </h1>
      <p style={{ color: "var(--muted)", marginTop: 0 }}>
        Each panel below uses one texture as its background (with the same dark overlay we'd use on
        the real sections, so you can judge readability). Tell me the number for each area:
        Studio · Now showing · Cards · Footer.
      </p>

      <div style={{ display: "grid", gap: "1.6rem", gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))", marginTop: "2rem" }}>
        {TEX.map((t) => (
          <div key={t.id}>
            <div
              style={{
                position: "relative",
                borderRadius: 18,
                overflow: "hidden",
                border: "1px solid var(--line-strong)",
                minHeight: 220,
                backgroundImage: `linear-gradient(rgba(24,16,8,.55), rgba(20,13,7,.72)), url(/tex/${t.key}.png)`,
                backgroundSize: "cover",
                backgroundPosition: "center",
                padding: "1.4rem",
                display: "flex",
                flexDirection: "column",
                justifyContent: "flex-end",
              }}
            >
              <span style={{
                position: "absolute", top: 12, left: 12,
                fontFamily: "var(--font-display)", fontWeight: 800, fontSize: "1.6rem",
                background: "linear-gradient(135deg,var(--amber-soft),var(--amber))",
                color: "#3a2410", border: "2px solid #1a1206", borderRadius: 999,
                width: 44, height: 44, display: "grid", placeItems: "center",
                boxShadow: "0 3px 0 #1a1206",
              }}>{t.id}</span>
              <h3 style={{ fontFamily: "var(--font-display)", margin: 0, fontSize: "1.5rem" }}>{t.label}</h3>
              <p style={{ color: "var(--muted)", margin: "0.3rem 0 0", fontSize: "0.9rem" }}>
                Sample body text to check how readable it stays on this texture.
              </p>
            </div>
            {/* also show it small, like a character card */}
            <div style={{ display: "flex", gap: "0.8rem", marginTop: "0.7rem", alignItems: "center" }}>
              <div style={{
                width: 90, height: 90, borderRadius: 14, border: "1px solid var(--line-strong)",
                backgroundImage: `linear-gradient(rgba(24,16,8,.35),rgba(20,13,7,.5)), url(/tex/${t.key}.png)`,
                backgroundSize: "cover", backgroundPosition: "center",
              }} />
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "var(--faint)" }}>
                #{t.id} · {t.key}<br />as a card background
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
