import { type Character, ossThumb } from "@/lib/api";

const EMOJI: Record<string, string> = {
  gallo: "🐔", vaca: "🐄", tractor: "🚜", cerdo: "🐖", gallina: "🐤",
};

export function CharacterRail({ characters }: { characters: Character[] }) {
  return (
    <div className="rail">
      {characters.map((c) => (
        <div className="char" key={c.name} title={c.personality}>
          {c.image_url ? (
            <img src={ossThumb(c.image_url, 96)} alt={c.name} loading="lazy" />
          ) : (
            <span style={{ fontSize: 30 }}>{EMOJI[c.species] ?? "🐾"}</span>
          )}
          <div className="who">
            <b>{c.name}</b>
            <span>{c.species}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
