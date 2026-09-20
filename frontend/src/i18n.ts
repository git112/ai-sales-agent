export const t = {
  en: {
    product: "Lumina",
    tagline: "From buying signals to qualified sales opportunities.",
    demo: "DEMO MODE",
    live: "LIVE MODE",
  },
  hi: {
    product: "Lumina",
    tagline: "खरीद संकेतों से योग्य बिक्री अवसरों तक।",
    demo: "डेमो मोड",
    live: "लाइव मोड",
  },
  gu: {
    product: "Lumina",
    tagline: "ખરીદ સંકેતોથી લઈને યોગ્ય વેચાણ તકો સુધી.",
    demo: "ડેમો મોડ",
    live: "લાઇવ મોડ",
  },
} as const;

export type Locale = keyof typeof t;
