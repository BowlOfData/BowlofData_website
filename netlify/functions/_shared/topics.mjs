// Topic metadata (labels / h1 / intro) — mirrors CATEGORY_META in build.py.
// Keyword classification lives in Python (done at load time); the functions only
// need presentation strings here.
export const CATEGORY_ORDER = ["ai", "security", "blockchain", "engineering"];

export const CATEGORY_META = {
  ai: {
    label: "AI & ML",
    h1: "AI & Machine Learning",
    intro:
      "Every week, Bowl of Data tracks the AI and machine-learning stories that " +
      "matter — new model releases, research that holds up, and where large models " +
      "actually land in real products. Here is every issue's AI coverage, newest first.",
  },
  security: {
    label: "Cybersecurity",
    h1: "Cybersecurity",
    intro:
      "Every week, Bowl of Data tracks the vulnerabilities, exploits, and threat " +
      "intelligence worth acting on — what to patch before it becomes someone else's " +
      "headline. Here is every issue's security coverage, newest first.",
  },
  blockchain: {
    label: "Blockchain & Crypto",
    h1: "Blockchain & Crypto",
    intro:
      "Every week, Bowl of Data tracks the meaningful moves in blockchain and crypto — " +
      "protocol upgrades, market shifts, and the regulation worth watching. Here is " +
      "every issue's blockchain coverage, newest first.",
  },
  engineering: {
    label: "Software Engineering",
    h1: "Software Engineering",
    intro:
      "Every week, Bowl of Data tracks the tools, frameworks, and open-source releases " +
      "that change how we build software. Here is every issue's engineering coverage, " +
      "newest first.",
  },
};
