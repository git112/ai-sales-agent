export const t = {
  en: {
    product: "Lumina",
    tagline: "From buying signals to qualified sales opportunities.",
    demo: "Standard Engine",
    live: "Production Engine",
  },
  hi: {
    product: "Lumina",
    tagline: "खरीद संकेतों से योग्य बिक्री अवसरों तक।",
    demo: "मानक इंजन",
    live: "उत्पादन इंजन",
  },
  gu: {
    product: "Lumina",
    tagline: "ખરીદ સંકેતોથી લઈને યોગ્ય વેચાણ તકો સુધી.",
    demo: "સ્ટાન્ડર્ડ એન્જિન",
    live: "પ્રોડક્શન એન્જિન",
  },
} as const;

export type Locale = keyof typeof t;
