export function verifiedLabel(verified: number, total: number): string {
  return `${verified} of ${total} verified`;
}

export function verifyPassesLabel(passes: number | null, samples: number | null): string {
  if (passes === null || samples === null) return "Not run";
  return `${passes} of ${samples}`;
}

const SHORT_ID_LENGTH = 8;

export function shortId(id: string): string {
  return id.slice(0, SHORT_ID_LENGTH);
}
