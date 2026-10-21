function parseTags(raw: string): string[] {
  return raw
    .split(',')
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
}

export function mergeTags(existing: string[], raw: string): string[] {
  const out = [...existing];
  for (const tag of parseTags(raw)) {
    if (!out.some((t) => t.toLowerCase() === tag.toLowerCase())) out.push(tag);
  }
  return out;
}
