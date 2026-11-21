/** `text` indented when it is JSON, unchanged otherwise. Also says which it was. */
export function prettyJson(text: string): { text: string; isJson: boolean } {
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed === null || typeof parsed !== "object") return { text, isJson: false };
    return { text: JSON.stringify(parsed, null, 2), isJson: true };
  } catch {
    return { text, isJson: false };
  }
}
