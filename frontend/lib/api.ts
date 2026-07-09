export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Character = {
  name: string;
  species: string;
  personality: string;
  image_url: string | null;
};

export type Take = {
  attempt: number;
  video_url: string;
  thumbnail_url: string;
  keyframe_prompt: string;
  motion_prompt: string;
  video_description: string;
  qa_status: string;
  qa_notes: string;
};

export type Episode = {
  id: number;
  creator: string | null;
  title: string | null;
  takes: Take[] | null;
  event: string | null;
  script: string | null;
  characters_used: string[] | null;
  video_prompt: string | null;
  video_tool: string | null;
  video_url: string | null;
  video_description: string | null;
  qa_status: string;
  qa_notes: string | null;
  qa_attempts: number | null;
  thumbnail_hint: string | null;
  thumbnail_url: string | null;
  description: string | null;
  status: string;
};

export async function getCharacters(): Promise<Character[]> {
  const res = await fetch(`${API}/characters`, { cache: "no-store" });
  if (!res.ok) throw new Error("No se pudieron cargar los personajes");
  return res.json();
}

export async function createCharacter(payload: {
  name: string;
  species: string;
  personality: string;
  look: string;
}): Promise<Character> {
  const res = await fetch(`${API}/characters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Could not create character");
  }
  return res.json();
}

export async function getEpisodes(): Promise<Episode[]> {
  const res = await fetch(`${API}/episodes`, { cache: "no-store" });
  if (!res.ok) throw new Error("No se pudo cargar el feed");
  return res.json();
}

export async function getEpisode(id: number): Promise<Episode> {
  const list = await getEpisodes();
  const found = list.find((e) => e.id === id);
  if (!found) throw new Error("Episodio no encontrado");
  return found;
}

/** Resize OSS images on the fly (cuts payload from ~1.4MB to a few KB). */
export function ossThumb(url: string | null | undefined, w: number): string | undefined {
  if (!url) return undefined;
  if (!url.includes("aliyuncs.com")) return url;
  return `${url}?x-oss-process=image/resize,w_${w}/quality,q_80/format,webp`;
}

export function streamEpisode(idea: string, creator: string) {
  const url = `${API}/episodes/generate/stream?idea=${encodeURIComponent(idea)}&creator=${encodeURIComponent(creator)}`;
  return new EventSource(url);
}
