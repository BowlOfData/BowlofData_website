# Services expansion: P0 validation pack

Gate for the **push** (plan E8). Nothing here blocks building or merging locally.

## 1. Gate table (owner fills in)
| Gate | Pass criterion | Result | Date |
|---|---|---|---|
| G1 Demand | 5 conversations with people running agent or LLM pilots; at least 3 say they would pay for a fixed-scope review. Fewer than 2: reshape (fold Secure into Build as a module). | | |
| G2 Deliverability | Marco can name every deliverable and the hours behind the Secure review (2 to 3 weeks) and the vendor report review (1 to 2 weeks) using sections 3 and 4 below. | | |
| G3 Wording | One security-literate outsider reads section 5 and does not push back on the Maki claim. | | |
| G4 References | Done by Claude, see section 2. | pass | 2026-10-18 |
| G5 Background | Marco confirms the generic regulated-industry wording may be published. | | |

Confirm each step actually happened (who, when) before using its result.

## 2. Regulatory reference check (G4, done)
- **DORA (Regulation (EU) 2022/2554), Chapter V, third-party risk.** Verified on EUR-Lex: Article 28 "General principles" (includes the obligation to maintain and update a register of information at entity, sub-consolidated and consolidated level), Article 29 "Preliminary assessment of ICT concentration risk at entity level", Article 30 "Key contractual provisions". The site names "Articles 28 to 30" only; it does not cite paragraph numbers (not individually confirmed).
- **BAIT.** The Bundesbank states BAIT "will be repealed completely with expiry of 31 December 2026". Institutions that must run ICT risk management under DORA Articles 5 to 15 or 16 are excluded from BAIT scope. ZAIT, VAIT and KAIT were repealed on 16 January 2025. Consequence: the earlier wording "former BAIT requirements" was wrong today; the site now says "and BAIT where it still applies". After 31 December 2026 the BAIT mention should be removed or turned into "former".
- **Not checked:** how MaRisk's IT provisions relate to DORA after 2025. The copy only says "what MaRisk and DORA expect"; do not add specifics until this is looked up.
- Sources: [Bundesbank BAIT/DORA page](https://www.bundesbank.de/en/tasks/financial-supervision/individual-aspects/risk-management/bait), [EUR-Lex 32022R2554](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554).

## 3. Agent & Guardrail Security Review: scope draft (G2)
**Inputs from the client:** architecture sketch of the agent or LLM app; list of tools, APIs and data sources it can reach; current system prompts and guardrail config; sample logs; names of the owner and the approver.
**Method (typical 2 to 3 weeks):**
1. Map: every tool or action an agent can call, with the credentials it uses and the data it can read or change.
2. Permissions: least-privilege check per tool; separation of read and write; human approval points for irreversible actions.
3. Tool-call control: is there an allowlist; are arguments validated; are unauthorized calls blocked and logged; where is the decision made (outside the model).
4. Audit: what is logged per action (who or what, tool, arguments, result, time); retention; can an action be reconstructed afterwards.
5. Prompt-injection exposure: untrusted content paths (documents, web, email) that reach a model with tool access; RAG source trust.
6. Output safeguards: toxic, biased and inaccurate output tests on a sample set; refusal and fallback behaviour; how failures are detected.
7. Private versus commercial AI: what data leaves the boundary, to which provider, under which terms.
**Deliverable:** prioritised findings (severity, evidence, recommended fix, effort), a one-page control map, and a proposed scope for implementation as a separate step.
**Not promised:** that nothing gets through; penetration testing of the client's infrastructure; certification.

## 4. AI Vendor Report Review: checklist and findings template (G2)
**Checklist (per SOC 2 report):**
- Type 1 or Type 2; period covered; report date and how stale it is.
- Auditor's opinion: unqualified or qualified; reasons.
- Trust services categories in scope (security always; availability, confidentiality, processing integrity, privacy optional).
- System description: does it cover the actual AI service you use (model API, data handling, retention, training on customer data)?
- Exceptions and deviations noted in the tests, and management responses.
- Subservice organisations (for example the cloud host) and whether they are carved out or included.
- Complementary user entity controls: the controls the vendor expects you to operate.
- Gaps between the report and ICT third-party expectations (DORA Articles 28 to 30): audit and access rights, sub-outsourcing, exit, incident reporting.
- Bridge letter or gap period since the report ended.
**Findings memo template:** vendor and service reviewed; report reviewed (type, period); summary (3 lines); findings table (item, evidence, risk, recommended action or question to the vendor); controls you must operate; open questions for the vendor; limitations ("review of the report only; not an audit; not an attestation").

## 5. Wording for the outsider read (G3)
Services page, Secure section: "What your agents can do, what your models can say, and what you can prove afterwards. Audit logging and blocking rules for unauthorized tool calls and agent actions. The aim is to reduce risk and give you evidence, not to promise that nothing gets through."
Why-us section: "Our security work follows the same pattern: Maki's built-in plugins are gated by allowlists, and because Maki is open source you can read how."
Question for the reader: does any sentence over-promise, and would you trust a team that said this?

## 6. Interview prompt for the 5 conversations (G1)
Opening: "We are considering a fixed-scope review of agents and LLM apps (what they can reach, what is logged and blocked, how output is safeguarded). Can I ask how you handle that today?"
Questions: Are agents or LLM apps with tool access in pilot or production? Who owns their security? What do you do today to control tool calls and log actions? What would make you hire outside help? Would a fixed 2 to 3 week review with prioritised findings be useful, and who would approve the budget? What would make it not worth it?
Close: ask for one introduction. Record: role, company type, pilots yes or no, would pay yes or no or maybe, objections.
