import { type Character, ossThumb } from "@/lib/api";

const ROLE: Record<string, string> = {
  gallo: "El líder sindical",
  vaca: "La romántica",
  tractor: "El indiferente",
  cerdo: "El filósofo",
  gallina: "La reportera",
};

export function CastGrid({ characters }: { characters: Character[] }) {
  return (
    <div className="cast-grid">
      {characters.map((c) => (
        <div className="cast-card" key={c.name}>
          <div className="pic">
            {c.image_url && <img src={ossThumb(c.image_url, 400)} alt={c.name} loading="lazy" />}
          </div>
          <div className="info">
            <b>{c.name}</b>
            <div className="role">{ROLE[c.species] ?? c.species}</div>
            <p>{c.personality}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
