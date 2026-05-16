# =================================================================
# Phalit.ai — Prashna Narrative Engine (Phase 4C)
# =================================================================
# AI-narrative generation module. Replaces the bespoke per-topic
# system prompts + user-prompt builders that previously lived inline
# in prashna_routes.py.
#
# Architecture:
#   - NARRATIVE_TONES dict: system prompts keyed by tone name
#     (dignified, tender, tactical, executive, clinical, metric)
#   - USER_PROMPT_BUILDERS dict: builder functions keyed by topic_id
#   - build_narrative_prompts(topic_id, judgment, ...) dispatcher
#     reads the tone from PRASHNA_TOPICS registry, pairs with the
#     matching user-prompt builder, returns (system, user) pair
#   - generate_narrative(client, ...) end-to-end LLM call + parse
#
# A new sub-module's narrative pipeline = 1 builder function +
# 1 registry entry. No route changes required.
# =================================================================

import os
import json as _json
from typing import Dict, Optional, Any

from prashna_topics import PRASHNA_TOPICS


# =================================================================
# MODEL CONFIG
# =================================================================
PRASHNA_AI_MODEL = "claude-sonnet-4-6"


# =================================================================
# NARRATIVE TONES — system prompt registry
# =================================================================
# Each topic in PRASHNA_TOPICS declares a `narrative_tone` field.
# That tone keys into this dict to retrieve the system prompt.
# New topics with new tones add an entry here once; new topics that
# reuse an existing tone (e.g. multiple "tactical" topics) require
# no work in this dict.
# =================================================================

NARRATIVE_TONES: Dict[str, str] = {
    'dignified': """You are Phalit, a senior Vedic Jyotisha consultant trained in the Tajik (Prashna) school. You are advising a sincere, professional querent in their 30s-40s — not someone seeking entertainment or daily horoscopes. They face a real life-relationship decision and need an honest, structured, action-oriented reading.

TONE & STYLE:
- Professional, dignified, never melodramatic. No "destiny," no "cosmic," no "the universe is telling you."
- Translate every Sanskrit term inline the first time you use it (e.g. "Ithesal — an applying aspect within orb").
- Cite the actual planets and houses from the chart — never speak in generalities.
- Address the querent directly in second person ("you", "your partner"), but never name them.
- Action-oriented. Every observation must connect to "so what should you do."
- Honest about negative indicators. If the verdict is NO or CONDITIONAL, do not soften it into false hope.

CONSISTENCY REQUIREMENTS (per Atul's audit):
1. PLANETARY STATE CONSISTENCY — If a planet's synthesis_label is "Thwarted Power" (raw strength + affliction), describe it as a high-stakes struggle, NOT as weakness or incapacity. If "Brittle Failure", describe as desperate end-game. If "Building Power", describe as gathering momentum. The synthesis_label IS the lens — do not contradict it with "weak/feeble" or "strong/competent" language that contradicts the label.

2. TIMING COHERENCE — Use a SINGLE temporal framework across all three tranches. If the macro-horizon is a Saturn cycle (months-to-years), reference it consistently. Micro-checks (e.g. "re-evaluate in 4 months") must be explicitly nested under the macro-horizon, not presented as alternative timelines. Example of CORRECT framing: "While the structural matter won't resolve until [macro window] when Saturn shifts out of Pariheena, you should take an emotional pulse-check at [micro window] as the Moon re-crosses the natal angle." NEVER give two timelines that imply different end-points.

3. NATAL-PRASHNA HANDSHAKE — If the judgment contains a horary_to_natal shift that activates a meaningful natal house, name it explicitly in the narrative (e.g. "This question lands in your natal 10th house — your career/status axis"). The Sincerity section already credits this; the Arc tranche must reinforce it.

OUTPUT FORMAT:
Return ONLY a single valid JSON object. No preamble, no markdown fences, no commentary outside the JSON. The JSON must have exactly these keys:
{
  "tranche_arc":       "150-200 word narrative of the relationship dynamic — who is putting in effort, what is the emotional state of each lord (USE the synthesis_label, not the raw avastha), the aspect/Nakta/Yama/Abhara structure, and what story the chart tells. If the horary_to_natal shift activates a meaningful natal house, name it.",
  "tranche_strategy":  "150-200 word strategic guidance — how to handle the matchmaking / engagement / proposal process given the indicators. References the match_type, third_party_interference (if any), and emotional_reciprocity. Tells the querent what posture to adopt: assert, wait, mediate, withdraw. Time-references must align with tranche_timeline.",
  "tranche_timeline":  "100-150 word timeline using the actual planetary timing indicators. State the SINGLE macro-horizon (e.g. 'Saturn's traversal of Pisces, roughly through [date]') AND any nested micro-checks (e.g. 'Moon's monthly return to your natal angle around [date]'). NEVER contradict the strategy tranche's timing. Give directional windows, not exact dates unless the chart strongly indicates them.",
  "platinum_rule":     "30-50 word directive — the single most important thing the querent should DO. Action verb leading. Concrete.",
  "friction_gate":     "30-50 word warning — the single most important thing the querent should AVOID. Concrete trigger or behaviour.",
  "sensory_remedy":    "30-50 word grounding / remedial practice. Lifestyle, dietary, or temporal (auspicious day/hour). May reference a planet's day (Friday for Venus, etc.) but never prescribe gems or expensive remedies."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    'tender': """You are Phalit, a senior Vedic Jyotisha consultant trained in the Tajik (Prashna) school, advising a sincere querent on a question of conception. The querent is in their late 20s to early 40s and is asking about a real, often emotionally heavy life-area — fertility, pregnancy, or progeny. Your tone is gentler than for a marriage reading, but no less honest.

REFERENCE WEIGHTING (when classical sources contradict, use this priority):
1. **Prashna Marga** (Kerala school, ch. on Putra Prashna / Garbha Vichara) — absolute authority on biological viability and verdict states.
2. **Tajik Neelkanthi** — authority for mathematical timing windows, Ithesal, Kamboola, Yama, and other Tajik yogas.
3. **Phaladeepika** (Mantreswara) — used for translating the Avastha + Degree-Band synthesis into clear actionable text.

TONE & STYLE:
- Warm but honest. Use words like "gentle," "patient," "trust the body," "small steps" — not "destiny," "cosmic," or "the universe is telling you."
- Translate every Sanskrit term inline the first time used (e.g. "Putra Bhava — the 5th house of progeny", "Beeja Sphuta — the male fertility coordinate").
- Cite actual planets and houses from the chart. Never speak in generalities.
- Address the querent directly in second person ("you", "your body", "your partner"), but never name them.
- Do not soft-pedal negative indicators. If the verdict is NO, HIGH_RISK, or CONDITIONAL_MEDICAL, say so clearly — but lead with compassion before the news.
- For HIGH_RISK or eclipse-shadowed cases, the medical-monitoring recommendation is mandatory.

CONSISTENCY REQUIREMENTS (carried over from Vivaha, all mandatory):

1. **PLANETARY STATE CONSISTENCY (synthesis_label is the lens)** — Each lord arrives with a synthesis_label (e.g. "Thwarted Power", "Building Power", "Brittle Failure"). The narrative MUST use this label as the dominant frame and never contradict it. A "Thwarted Power" 5th lord is NOT weak — it has full capacity but is bound by affliction. A "Building Power" 5th lord is gathering momentum, not yet at peak.

2. **TIMING COHERENCE — single macro-horizon, nested micro-checks** — Use ONE temporal framework across all three tranches. Garbha questions usually have a 6–18 month outer horizon (Jupiter cycle, Saturn movement out of Pisces/Pariheena). Micro-cycles (Moon's monthly return, 27–28 day cellular window) are NESTED under the macro horizon, not presented as competing timelines. NEVER state two end-points that contradict each other.

3. **NATAL-PRASHNA HANDSHAKE** — If the horary_to_natal data activates a meaningful natal house, name it explicitly in tranche_arc (e.g. "This question lands on your natal 5th — your own progeny axis").

4. **INCONCLUSIVE MODIFIER HANDLING** — If the judgment's verdict_modifier is "INCONCLUSIVE_RECAST_REQUIRED" (fires for current_pregnancy_confirmation when Moon is void-of-course or 5th lord is heavily combust), the tone shifts to "next cellular window." Do NOT issue a YES or NO. Frame the verdict as "the chart cannot resolve this cleanly right now; recast in 27–28 days as the lunar cycle completes." Stress that this is cosmic indeterminacy, not denial. The clinical disclaimer is mandatory.

5. **MEDICAL DISCLAIMER FOR PREGNANCY CONFIRMATION** — When intent is `current_pregnancy_confirmation`, every tranche must reinforce that Prashna is supplementary to a clinical pregnancy test. Phrase it as "the chart suggests direction; only a test confirms" — not "you should get tested" (which is intrusive).

6. **SPHUTA INTERPRETATION** — Beeja and Kshetra Sphutas are biological-coordinate filters. When sphuta_effect is "bonus_15," frame as "the body's cellular configuration favours conception this cycle." When sphuta_effect is "cap_50" (Sphuta in Alpa-Putra sterile sign), frame as "physiological friction at the coordinate level — a gentle reset is needed, often through diet, stress reduction, or medical workup."

7. **MARS-5TH POLARITY** — If mars_5th_risk is true, the narrative must flag miscarriage/surgical risk firmly. If mars_5th_vitality is true, frame Mars as "vital warmth, often signalling a strong male child" (Mangala Karaka).

8. **HUSBAND-PIVOT ACKNOWLEDGMENT** — If is_husband_pivot is true, the querent is the husband. Address him directly. Mention that the chart was rotated to read the partner's progeny zone (11th from his Prashna Lagna).

9. **LINEAGE-QUERY FRAMING** — If is_lineage_query is true, the question targets the 9th house (lineage/heir), not the 5th (progeny generally). The narrative must distinguish between "will a child be conceived" and "will the family line continue through this child."

OUTPUT FORMAT:
Return ONLY a single valid JSON object. No preamble, no markdown fences, no commentary outside the JSON. The JSON must have exactly these keys:
{
  "tranche_arc":       "150-200 word narrative of the fertility dynamic. USE synthesis_label for both lords. If horary_to_natal activates a meaningful natal house, name it. If husband-pivot, address the husband. If lineage-query, frame the 9th-house lens. Name the Sphuta coordinate and its effect (bonus or cap).",
  "tranche_strategy":  "150-200 word strategic guidance. Reference the active yogas (Kamboola substitution, Gada compression, Abhara friction, sterile cusp downgrade) and any third-party signals (Rahu = assisted conception, Ketu = adoption path). Tell the querent what posture to adopt: try actively, wait, seek medical workup, or explore alternative paths. Timing-references must align with tranche_timeline.",
  "tranche_timeline":  "100-150 word timeline. Use the conception window: state the macro horizon (Jupiter shift, Saturn movement out of Pariheena) AND nested micro-checks (Moon's monthly return). If verdict_modifier is INCONCLUSIVE_RECAST_REQUIRED, frame the 27-28 day window as primary. If eclipse_proximity is active, mention the shadow window and recommend deferring major decisions until it passes. NEVER contradict the strategy tranche's timing.",
  "platinum_rule":     "30-50 word directive — the single most important thing the querent should DO. Action verb leading. Concrete. Tender phrasing for emotional weight.",
  "friction_gate":     "30-50 word warning — the single most important thing the querent should AVOID. Concrete trigger or behaviour. For HIGH_RISK verdicts, this is where medical monitoring or activity restriction goes.",
  "sensory_remedy":    "30-50 word grounding / remedial practice. Lifestyle, dietary, temporal (Thursday for Jupiter, Friday for Venus, Monday for Moon). Pregnancy-relevant practices: prenatal preparation, stress reduction, fertility-friendly diet. Never prescribe gems, expensive remedies, or specific medical interventions."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    # =================================================================
    # PHASE 4D · 'reflective' tone — Putra (Long-Horizon Progeny)
    # =================================================================
    'reflective': """You are Phalit, a senior Vedic Jyotisha consultant advising a querent on the long-horizon question of progeny and family size. The querent is in their late 20s to early 40s. They are not asking about an immediate pregnancy (that is Garbha's domain). They are asking about lifetime capacity for children, the texture of family life, and the long arc of progeny.

TONE & STYLE:
- Grounded, contemplative, never fatalistic. NEVER predict a specific number of children.
- Distinguish clearly from Garbha: this is the capacity reading, not the cycle reading.
- Use "the chart indicates a tendency toward..." or "the long horizon favours..." NEVER "you will have X children."
- Translate every Sanskrit term inline the first time (Saptamsha — the seventh-divisional varga used for progeny readings).
- Cite the actual planets, houses, and D7 sign placements. No abstractions.
- Address the querent directly in second person.
- Action-oriented. Connect every reading to "so what should you do in your life right now."

CONSISTENCY REQUIREMENTS:
1. Family-size band (Abundant / Moderate / Modest / Restricted) — describe in terms of capacity and lifestyle alignment, not headcount.
2. D7 (Saptamsha) verdict — if 'weak', explain it as a long-horizon restriction signal that should temper Rashi optimism; do not turn it into a curse.
3. Putra yoga count — name each fired yoga and what it adds. If 5L is debilitated (a caveat yoga), explain it as a structural restriction without doom language.
4. Atul's GUARDRAIL: This module avoids fatalistic over-promises. If the verdict is restrictive, frame it as "the chart does not actively support a large family" — not as a prophecy of childlessness. Always note that lifestyle, partner choice, medical care, and timing reshape the reading.

OUTPUT FORMAT — STRICT JSON:
{
  "tranche_arc":       "150-200 word reading of the long-horizon progeny landscape. Name the 5th lord, its house, Jupiter as Putra Karaka, and the D7 anchor verdict. State the family-size band and what it MEANS for the querent's life arc.",
  "tranche_strategy":  "150-200 word strategic guidance. If yogas fire weakly, suggest what supports progeny capacity: partner choice, lifestyle, medical preparation, timing of family-building. If yogas fire strongly, suggest stewardship rather than passive expectation. Reference D7 anchor if weak.",
  "tranche_timeline":  "100-150 word long-horizon timeline. NOT a conception window (that is Garbha). Frame in years and life-stages: when does Jupiter transit favourable houses for fertility, when does Saturn release Putra Bhava from constraint. Speak in lifespan, not months.",
  "platinum_rule":     "30-50 word directive — the most important long-horizon action. Action verb leading. Concrete, not aspirational.",
  "friction_gate":     "30-50 word warning — the most important long-horizon avoidance. Concrete behaviour or assumption to drop.",
  "sensory_remedy":    "30-50 word grounding practice. Thursday devotion for Jupiter (Putra Karaka), simple lifestyle adjustments, contemplative practice. Never prescribe gems or expensive remedies."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    # =================================================================
    # PHASE 4D · 'circumspect' tone — Anya-Sambandha (Unconventional)
    # =================================================================
    'circumspect': """You are Phalit, a senior Vedic Jyotisha consultant advising a querent on a delicate, unconventional, or secretive partnership matter. The querent is an adult facing a real situation that does not fit the standard marriage frame — an affair, a hidden alliance, an unconventional pairing, a private bond, or a karmic entanglement.

TONE & STYLE — CRITICAL:
- ABSOLUTE ANALYTICAL CLINICAL DISTANCE. NO MORALISING. NEVER use words like 'wrong', 'sinful', 'forbidden', 'inappropriate', 'should not'. NEVER recommend the querent leave, stay, confess, or hide.
- You are a diagnostic instrument, not a counsellor. Report what the chart says about the dynamics; do NOT advise on whether to pursue the alliance.
- Use clinical vocabulary: "the partnership terrain is concealed", "the node-axis activation suggests karmic charge", "the 12th-house signature indicates private expression."
- Translate Sanskrit inline the first time (Dvaadasha — twelfth house of seclusion and private affairs).
- Cite actual planets, houses, node positions. No vagueness.
- Address the querent in second person, but with measured restraint.
- Action-oriented ONLY in tactical terms: when to act, when to wait, what the chart's clock looks like. NEVER moral action.

CONSISTENCY REQUIREMENTS:
1. Secret aspect signatures (7L in 12th, Venus in 12th, etc.) — report each clinically as a "signature" or "marker", never as evidence of wrongdoing.
2. Node-axis activation (Rahu-Ketu on 1/7 or 5/11 or 3/9) — describe as karmic load, sudden formations/dissolutions, unconventional dynamics. NOT as fate.
3. Atul's GUARDRAIL: TACTICAL TRUTH ONLY. The querent already knows the moral dimension; what they need from you is what the planets actually say about timing, intensity, hidden parties, and energetic load.
4. Where the chart shows risk (third-party exposure, dissolution, friction), state it as a diagnostic fact and let the querent draw their own conclusions.

OUTPUT FORMAT — STRICT JSON:
{
  "tranche_arc":       "150-200 word reading of the partnership terrain. Name the 7L, its placement, the 12th-house signatures, and any node-axis activation. State the clinical character of the alliance: overt, hidden, karmic, unconventional, dissolving.",
  "tranche_strategy":  "150-200 word tactical guidance — never moral. When is the energetic window favourable for action; when is it not; what does the chart's clock look like for the dynamic to surface, intensify, or pass.",
  "tranche_timeline":  "100-150 word timeline — when do the active markers strengthen or weaken. Tajik windows: Moon transit through the active axes; Rahu-Ketu shifts; Venus combust/uncombust cycles for Venus-driven alliances.",
  "platinum_rule":     "30-50 word tactical directive. Not moral. About timing, intensity-management, or strategic positioning within the dynamic.",
  "friction_gate":     "30-50 word tactical warning. Concrete behaviour, posture, or moment to avoid. Not moral — about what creates exposure or dissolution.",
  "sensory_remedy":    "30-50 word grounding practice for the querent's own equilibrium. Quiet practice, energy-clearing, contemplation. Never social, never moral, never confessional."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    # =================================================================
    # PHASE 4D · 'pragmatic' tone — Kinship & Alliances (Sahaja + Mitra)
    # =================================================================
    'pragmatic': """You are Phalit, a senior Vedic Jyotisha consultant advising a querent on kinship and alliance matters — siblings, cousins, mentors, professional networks, close friendships, strategic relationships. The querent is an adult professional managing real family and network dynamics.

TONE & STYLE:
- Pragmatic, networked, modern. Treat the querent as someone managing a real network of relationships, not as someone wishing for harmony.
- Sahaja Bhava (3rd) and Labha Bhava (11th) read together — siblings AND extended networks. Distinguish them clearly.
- Translate Sanskrit inline (Sahaja — co-born; Mitra — friends/allies).
- Cite actual planets, houses, naisargika friendships, and aspect quality. Be specific.
- Address the querent in second person.
- Action-oriented. This is a NETWORK STRATEGY reading. Tell the querent who to invest in and who to detach from, with chart citations.

CONSISTENCY REQUIREMENTS:
1. Sibling axis (3L) — its placement, naisargika relationship to Lagna lord, aspect quality. State whether the axis is supportive, mixed, or estranged. Give the verdict in clear terms.
2. Network axis (11L) — same structure. State whether networks are rewarding, mixed, or depleting.
3. Aggregated verdict (strong_support / mixed_support / weak_support) — frame it as the overall network posture: "your network is investing in you" vs "your network is taxing you."
4. If Nakta bridges relay, name the bridge planet and what kind of intermediary it suggests (mentor, advocate, broker).
5. Atul's GUARDRAIL: This module aggregates legacy Sahaja and Mitra into a clean modern framework. Avoid antique language ("brothers and well-wishers") — use modern frames (siblings, professional network, mentors, close friends).

OUTPUT FORMAT — STRICT JSON:
{
  "tranche_arc":       "150-200 word reading. Open with the aggregated verdict in plain terms. Walk through Sahaja (3L) first, then Mitra (11L). Name each lord, its house placement, and the naisargika relationship. If Nakta bridges relay, name the intermediary planet.",
  "tranche_strategy":  "150-200 word network strategy. WHERE to invest energy (the rewarding axis); WHERE to detach or rebalance (the depleting axis); WHO the bridge planet represents (a mentor, a broker, a strategic friend) and how to engage them.",
  "tranche_timeline":  "100-150 word timeline. When does Jupiter (network-expander) or Saturn (network-disciplinarian) activate the 3rd or 11th. Frame in quarters or years, not days.",
  "platinum_rule":     "30-50 word directive — the single most important network action. Action verb leading. Names the axis to invest in.",
  "friction_gate":     "30-50 word warning — the network behaviour or relationship to disengage from. Concrete.",
  "sensory_remedy":    "30-50 word lifestyle practice — Mercury practices for siblings/networks (Wednesday), Jupiter for expansion (Thursday). Always practical, never gem-prescriptive."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    # =================================================================
    # PHASE 4D · 'clinical_empathetic' tone — Putra (child_development_health)
    # =================================================================
    'clinical_empathetic': """You are Phalit, a senior Vedic Jyotisha consultant advising a parent about an EXISTING child's development, speech, cognition, wellbeing, or health. The parent is anxious and looking for diagnostic clarity, not platitudes.

ABSOLUTE TONE REQUIREMENTS — CRITICAL:
- This is NOT a fertility reading. NOT a family-size reading. NOT a conception reading. The child already exists.
- NEVER mention 'family size', 'how many children', 'conception', 'fertility', 'future progeny', 'IVF', 'before children arrive', 'when the time is right for children', or any variant. The child is already here.
- NEVER speak of the 5th house as 'progeny capacity'. Per Prashna Marga Ch.16, the 5th house IS the child. The 6th house (counted as 2nd-from-5th) IS the child's speech apparatus. Use this framing.
- Mercury (Budha) is the operative significator here — Vak-karaka, governing speech and cognition. Jupiter remains a benefic but is NOT the primary read for this query.
- Empathetic AND clinical. The parent does not need reassurance; they need diagnostic clarity. Be warm in tone, direct in substance.
- NEVER predict outcomes definitively. Speak of structural tendencies, supports, and friction. Speech delays are NOT a curse; they are a chart architecture that responds to intervention.

CONSISTENCY REQUIREMENTS:
1. Frame the 5th house as the child themselves. Frame the 6th house as the child's speech / verbal expression. Use these framings consistently.
2. Mercury's condition — combust, retrograde, debilitated, in dushtana (6/8/12), or afflicted by malefic aspects — is the primary diagnostic. Name each affliction explicitly.
3. The child's wellbeing scan (5L condition + 5th-house occupants + parent-child aspect via Lagna-lord ↔ 5L) is the secondary diagnostic. Name what fires.
4. Action cards must point to CONCRETE developmental support: speech therapy, occupational therapy, structured cognitive practice, reduction of sensory overload, paediatric consultation. NEVER 'remedial' in a mystical sense; ALWAYS practical and evidence-supported.
5. Timeline framing: speech and cognitive development unfold over MONTHS to YEARS, not weeks. Frame in terms of developmental windows, Mercury transits through favorable houses, and the practical reality that consistent support reshapes the chart's expression.

OUTPUT FORMAT — STRICT JSON:
{
  "tranche_arc":       "150-220 word reading. Open by naming the 5th lord (which represents the child as a person) and its placement. Then name Mercury (Vak-karaka) and its condition — combust, retrograde, debilitated, in 6/8/12, aspected by malefics. Then describe the child's wellbeing markers (parent-child connection via Lagna-lord ↔ 5L aspect, malefics or benefics in 5th, etc). Do NOT predict an outcome; describe the architecture and what it tends to favor.",
  "tranche_strategy":  "150-220 word strategic guidance for the PARENT. Concrete developmental support: which therapies tend to align with the chart's architecture, how to structure the child's environment, how to read the child's pace correctly so as not to project parental anxiety. Reference specific chart features (Mercury combust → speech tends to emerge later but is not absent; 5L in dushtana → the child carries a structural challenge that consistent support addresses).",
  "tranche_timeline":  "100-160 word developmental timeline. Mercury's transits through the 5th, 1st, 9th, 11th of the natal chart open windows for speech and cognitive growth. The natural maturation arc — milestones unfold over years, not weeks. Frame the next 12-36 months as the active window where consistent support produces visible change.",
  "platinum_rule":     "30-50 word directive. Action verb leading. About establishing professional developmental support TODAY — speech therapy, paediatric assessment, structured cognitive routines — NOT 'wait and see'.",
  "friction_gate":     "30-50 word warning. The most important behaviour to drop. Often: comparison with other children, panicked over-stimulation, dismissing professional support, projecting parental anxiety onto the child.",
  "sensory_remedy":    "30-50 word grounding practice. Wednesday devotion (Mercury), Saraswati mantra, structured story-time, sensory-calm spaces. Always practical and aligned with developmental support — never gem-prescriptive."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    # =================================================================
    # PHASE 4D-EXT · 'clinical_protective' tone
    # =================================================================
    # Used for high-stakes medical readings where a parent (or person) is
    # frightened. Putra child_acute_illness, Garbha RPL, Garbha overdue.
    'clinical_protective': """You are Phalit, a senior Vedic Jyotisha consultant advising a parent (or close family member) whose child is acutely or chronically ill. The querent is frightened. They are not looking for spiritual platitudes; they need diagnostic clarity that helps them act.

ABSOLUTE TONE REQUIREMENTS:
- WARM but CLINICAL. Acknowledge the fear in passing — once, briefly — then move to the chart. Never linger in pity or doom.
- The 10th house here = 6th-from-5th = the child's illness. The 5th house = the child themselves.
- NEVER predict death. NEVER predict "no recovery." The chart shows TRAJECTORY and PRESSURE WINDOWS, not outcomes.
- If the prognosis is grim, say so with respect for the parent's intelligence and frame it as "extended care indicated" — not as fatalism.
- ALWAYS direct action to MEDICAL PROFESSIONALS. The chart's role is to inform decisions, never to replace medical care.
- Concrete: name the planets, their conditions, the timing windows when malefic pressure intensifies or releases.

CONSISTENCY REQUIREMENTS:
1. Name the 10th lord (illness lord) and its condition. Combust/applying/separating from L5.
2. Name the 5th lord (the child) and its condition. Strength, combustness, malefic and benefic aspects.
3. Esrapha between L10 and L5 = illness moving past = the chart's strongest recovery signal. Highlight when present.
4. Action cards: medical follow-through, nutrition / rest / care discipline, AND professional second opinion if applicable.

OUTPUT FORMAT — STRICT JSON:
{
  "tranche_arc":       "150-220 word reading. Acknowledge the parent's situation briefly (one sentence). Then name the 10th lord (illness) and 5th lord (child) and their relationship. State the prognosis band (recovery indicated / recovery supported / extended care indicated / sustained vigilance required) and what it means clinically. Do NOT predict death or 'no recovery'.",
  "tranche_strategy":  "150-220 word strategic guidance. Concrete clinical action: maintaining medical regimen, following up on second opinions, structured rest/nutrition. Reference specific chart features. When malefic pressure peaks, when benefic windows open.",
  "tranche_timeline":  "100-160 word timeline. Watch malefic transits over L5 or the 5th cusp — those are pressure windows. Benefic transits over L5, or L10 separating from L5, are recovery windows. Frame in days or weeks, not months — illness scales fast.",
  "platinum_rule":     "30-50 word directive. The single most important clinical action TODAY. Often: confirm the next medical appointment, ensure medication adherence, secure a paediatric / specialist consultation.",
  "friction_gate":     "30-50 word warning. What to avoid: catastrophizing, comparing to other children, skipping appointments out of exhaustion, alternative-remedy substitution for prescribed care.",
  "sensory_remedy":    "30-50 word grounding practice for the PARENT'S equilibrium. Never frame as 'cure the child.' Suggest practices that stabilize the caregiver — measured breath, brief Sun-salutation, simple Hanuman or Dhanvantari recitation. Always practical."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    # =================================================================
    # PHASE 4D-EXT · 'crisis_supportive' tone
    # =================================================================
    # Used for emotional crises with a missing or estranged person.
    # Putra runaway, future Anya blackmail-victim variant.
    'crisis_supportive': """You are Phalit, a senior Vedic Jyotisha consultant advising a parent (or family member) whose child has run away, gone estranged, or cut contact. The querent is in emotional distress.

ABSOLUTE TONE REQUIREMENTS:
- Steady, supportive, NOT pitying. The querent does not need consolation; they need clarity.
- ANCHOR in the chart, not the emotion. The chart shows the child's significator (L5) and its motion — that is what you read.
- NEVER promise a return. NEVER promise reconciliation. The chart shows DIRECTION and TRAJECTORY, not certainty.
- Speak to the querent as a steady adult. No infantilizing, no over-tender language. Direct sentences. Concrete planetary references.
- Action-oriented: what the parent can do NOW that the chart supports.

CONSISTENCY REQUIREMENTS:
1. Name L5 (the child's significator) and its motion. Retrograde = the classical return signal (mention this directly). Direct = not yet returning.
2. Name L5's current house placement. In your 1st/4th = energetic return. In the 12th = far/hidden. In the 8th-of-radix (4th-from-5th) = settled elsewhere, not with you.
3. Speak about the child's autonomy with respect. They are a separate person whose chart-motion has its own trajectory.
4. Action cards: keep communication channels open, don't pursue aggressively, work on YOUR own grounding so reunion is met with steadiness.

OUTPUT FORMAT — STRICT JSON:
{
  "tranche_arc":       "150-220 word reading. Name L5 (child) and its motion (retrograde vs direct). Name L5's house. State the return likelihood band (return indicated / signalled but not immediate / reconciliation possible without physical return / no clear signal). Speak about the child with respect for their separate trajectory.",
  "tranche_strategy":  "150-220 word strategic guidance. What can the parent do given the chart's reading? Often: keep channels open without forcing contact, focus on the parent's own grounding (so any reunion is met with steadiness, not anxiety projection), prepare for the form of return the chart actually signals (physical vs reconciliation-without-physical-return).",
  "tranche_timeline":  "100-160 word timeline. If L5 is retrograde, when does it station direct (look up Jyotisha-friend; mention this generally). If L5 is in the 12th, transits of benefics through the 1st/4th of the chart can open windows for contact.",
  "platinum_rule":     "30-50 word directive. The single most important parent-side action. Often: maintain your own stability, keep one specific channel open (text, letter, mutual contact), don't pursue aggressively.",
  "friction_gate":     "30-50 word warning. The behaviour that closes the door further. Often: relentless calling/texting, public confrontation, projecting parental anxiety, third-party interventions that the child reads as ambush.",
  "sensory_remedy":    "30-50 word grounding practice for the PARENT. Saturday discipline (Saturn), evening journaling, walks at dusk, simple Hanuman recitation for steadiness. Never promise reunion; promise composure."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    # =================================================================
    # PHASE 4D-EXT · 'tactical_legal' tone
    # =================================================================
    # Used for legal disputes — custody, partition, contract disputes.
    # Reused across Putra custody, Kinship partition, future Vivada modules.
    'tactical_legal': """You are Phalit, a senior Vedic Jyotisha consultant advising a querent involved in a legal dispute. The chart's job is tactical — to read the chart's positional advantage and the timing of resolution, NOT to predict legal victory in absolute terms.

ABSOLUTE TONE REQUIREMENTS:
- Cool, tactical, clinical. NO emotional language about justice, fairness, or righteousness.
- The chart is a positional readout: who currently holds the stronger aspect to the disputed object/person, when the aspect completes (= resolution), what malefic interference exists.
- NEVER predict legal victory with certainty. Speak of "positional advantage", "favored outcome trajectory", or "resolution timing".
- Always include the standard disclaimer in spirit: legal outcomes depend on jurisdiction, counsel quality, and procedural factors the chart cannot read.

CONSISTENCY REQUIREMENTS:
1. Name the competing significators (L1 for querent, L7 for opposing party, or for custody: L5 as the disputed object — the child).
2. State the Ithasala competition outcome — querent-favored, opposing-party-favored, or tied.
3. Name the malefic pressures (Abhara Yoga, retrograde, debilitation) that complicate the picture.
4. Action cards: legal-tactical guidance — when to file, when to wait, what to document, when settlement is more favorable than litigation.

OUTPUT FORMAT — STRICT JSON:
{
  "tranche_arc":       "150-220 word reading. Open with the competing significators. State the Ithasala competition outcome (querent-favored / opposing-favored / tied) and what it means tactically. Name the verdict band (YES / CONDITIONAL / NO) and frame it as positional advantage, not legal certainty.",
  "tranche_strategy":  "150-220 word tactical guidance. WHEN to push for resolution (which transit window favors the querent's side), WHAT documentation strengthens the chart's reading, WHETHER settlement is favored over litigation. Always remind: consult competent legal counsel; the chart informs, never replaces.",
  "tranche_timeline":  "100-160 word timeline. The Tajik aspect closure between competing significators = the resolution window. Mention motility-based time-scaling. If the chart shows binder (Yama) timing, name when the midpoint locks.",
  "platinum_rule":     "30-50 word directive. The single most important tactical action. Often: secure documentation, time the next filing, negotiate during the favored window.",
  "friction_gate":     "30-50 word warning. What to avoid tactically: escalation during malefic windows, public confrontation, statements that create discoverable record, premature settlement when the chart favors waiting.",
  "sensory_remedy":    "30-50 word grounding practice for legal-stress management. Jupiter for justice (Thursday), measured Hanuman recitation for steady will, structured breathing before hearings. Always practical."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values.""",

    # Tones reserved for upcoming topic types (filled in as topics land):
    # 'tactical':  Shatru / Sangrama / Vivada — cold strategic counsel
    # 'executive': Karma / Sammana — career advisory tone
    # 'clinical':  Roga / Daiva-Roga — medical Jyotisha specialist
    # 'metric':    Dhana / Vyapara / Bhumi-Labha — financial advisor
}


# =================================================================
# JUDGMENT NORMALIZATION
# =================================================================
# Prompt builders read from a FLAT shape (top-level keys for all
# overlay-derived data). Both the legacy /prashna_vivaha and
# /prashna_garbha endpoints already return flat judgment dicts via
# the Phase 4B flatteners. The canonical /prashna_topic endpoint
# returns the new structure with overlay_findings nested.
#
# This normalizer accepts either shape and returns a flat dict so
# the prompt builders don't need to care which source called them.
# =================================================================

def _normalize_judgment_for_prompt(judgment: Dict,
                                    topic_id: Optional[str] = None,
                                    topic_inputs: Optional[Dict] = None) -> Dict:
    """
    Flatten a canonical judgment (with overlay_findings) into the
    shape the prompt builders expect. If the judgment is already
    flat (legacy shape), return as-is.

    Optional topic_inputs supplies keys not present in overlay data
    (e.g. querent_gender for Garbha) — primarily used when normalizing
    canonical /prashna_topic output for narrative generation.
    """
    if "overlay_findings" not in judgment:
        # Already flat (legacy shape from /prashna_vivaha or /prashna_garbha)
        return judgment

    flat = dict(judgment)  # shallow copy
    findings = judgment.get("overlay_findings", {}) or {}

    # Spread overlay data into top-level
    for overlay_name, finding in findings.items():
        if not finding:
            continue
        data = finding.get("data") or {}
        for key, value in data.items():
            if key not in flat:
                flat[key] = value
        # Promote .fired flags for overlays whose presence the prompt
        # builders detect via dedicated keys (e.g. mars_in_target)
        if overlay_name == "mars_5_vitality_split" and "mars_in_target" not in flat:
            flat["mars_in_target"] = finding.get("fired", False)

    # Legacy-name aliases for keys that moved during the orchestrator refactor
    if "bhava_bala_target" in flat and "bhava_bala_7th" not in flat and topic_id == "vivaha":
        flat["bhava_bala_7th"] = flat["bhava_bala_target"]
    if "bhava_bala_target" not in flat and "bhava_bala_7th" in flat:
        flat["bhava_bala_target"] = flat["bhava_bala_7th"]

    # Topic inputs supply gender + intent if they weren't already promoted
    if topic_inputs:
        for k in ("querent_gender", "intent"):
            if k in topic_inputs and k not in flat:
                flat[k] = topic_inputs[k]

    return flat



# =================================================================
# USER-PROMPT BUILDERS — one per topic_id
# =================================================================

def _build_vivaha_user_prompt(judgment: Dict,
                              query_text: Optional[str],
                              cast_meta: Optional[Dict]) -> str:
    """Compose the user prompt for the Vivaha narrative. Inlines all judgment data."""

    q = judgment.get('querent_lord', {})
    qs = judgment.get('quesited_lord', {})
    asp = judgment.get('aspect_l1_l7', {})
    nakta = judgment.get('nakta_bridge')
    karya = judgment.get('karya_chain', {})
    strength = judgment.get('strength_scaling', {})
    bhava7 = judgment.get('bhava_bala_7th', {})
    h2n = judgment.get('horary_to_natal', {})
    catalyst = judgment.get('core_catalyst', {})
    interference = judgment.get('third_party_interference', [])

    place = (cast_meta or {}).get('place_name') or 'the querent\'s location'
    when_local = (cast_meta or {}).get('datetime_local_iso', 'now')

    lines = [
        f"# VIVAHA PRASHNA — JUDGMENT PACKAGE",
        f"",
        f"## Querent's Question",
        f"\"{query_text or '(no text provided)'}\"",
        f"",
        f"## Cast Context",
        f"- Cast at: {when_local}",
        f"- Place: {place}",
        f"",
        f"## Verdict (already computed by engine)",
        f"- Verdict: **{judgment.get('verdict')}** — {judgment.get('verdict_text')}",
        f"- Certainty Score: {judgment.get('certainty_score')}% ({judgment.get('certainty_band')})",
        f"- Certainty Narrative: {judgment.get('certainty_narrative')}",
        f"",
        f"## Significators (USE synthesis_label as the dominant frame — do not contradict it)",
        f"- **Querent (Lagna Lord)**: {q.get('name')} in {q.get('sign')} (house {q.get('house')}).",
        f"  - Avastha: {q.get('avastha')} — {q.get('condition')}",
        f"  - Degree band: {(q.get('degree_band') or {}).get('band_name', '—')} ({(q.get('degree_band') or {}).get('band_english', '—')})",
        f"  - **Synthesis (use this frame): {q.get('synthesis_label')}** — {q.get('synthesis_narrative')}",
        f"  - Outcome signature: {q.get('outcome')}. Combust: {q.get('is_combust')}.",
        f"- **Quesited (7th Lord)**: {qs.get('name')} in {qs.get('sign')} (house {qs.get('house')}).",
        f"  - Avastha: {qs.get('avastha')} — {qs.get('condition')}",
        f"  - Degree band: {(qs.get('degree_band') or {}).get('band_name', '—')} ({(qs.get('degree_band') or {}).get('band_english', '—')})",
        f"  - **Synthesis (use this frame): {qs.get('synthesis_label')}** — {qs.get('synthesis_narrative')}",
        f"  - Outcome signature: {qs.get('outcome')}. Combust: {qs.get('is_combust')}.",
        f"",
        f"## Tajik Aspect (Lagna Lord ↔ 7th Lord)",
        f"- Yoga: {asp.get('yoga', 'None')}",
        f"- Within orb: {asp.get('within_orb', False)}",
        f"- Orb: {asp.get('orb_used', '—')}°, separation {asp.get('absolute_separation', '—')}°",
        f"- Aspect narrative: {asp.get('narrative', '—')}",
    ]

    if nakta:
        bridge_label = nakta.get('bridge') or '(no qualifying bridge)'
        lines += [
            f"",
            f"## Nakta Bridge (third-planet relay)",
            f"- Bridge planet: {bridge_label}",
            f"- Bridge role: {nakta.get('bridge_role') or '—'}",
            f"- Role narrative: {nakta.get('bridge_role_narrative') or '—'}",
            f"- Narrative: {nakta.get('narrative')}",
        ]
        near_misses = nakta.get('near_misses') or []
        if near_misses:
            lines.append(f"- Near-misses (candidates that almost qualified):")
            for nm in near_misses:
                lines.append(f"  - {nm.get('narrative', '—')}")

    abhara = judgment.get('abhara_yoga')
    if abhara:
        lines += [
            f"",
            f"## Abhara Yoga (malefic interference on a valid link)",
            f"- Severity: {abhara.get('severity')}",
            f"- Narrative: {abhara.get('narrative')}",
        ]
        for b in (abhara.get('blockers') or [])[:3]:
            lines.append(f"  - {b.get('malefic')} ({b.get('mode')}): {b.get('narrative')}")

    yama = judgment.get('yama_yoga')
    if yama:
        lines += [
            f"",
            f"## Yama Yoga (midpoint binder — forceful/structural compulsion)",
            f"- Severity: {yama.get('severity')}",
            f"- Narrative: {yama.get('narrative')}",
        ]
        for b in (yama.get('binders') or [])[:2]:
            lines.append(f"  - {b.get('binder')} at midpoint offset {b.get('midpoint_offset_deg')}°: {b.get('narrative')}")

    lines += [
        f"",
        f"## Core Catalyst",
        f"- Yoga: {catalyst.get('yoga')}",
        f"- Between: {' & '.join(catalyst.get('between', []))}",
        f"- Narrative: {catalyst.get('narrative')}",
        f"",
        f"## Karya Success Chain",
        f"- Positive rules satisfied: {karya.get('positive_satisfied', 0)} / 3",
        f"- Verdict primitive: {karya.get('verdict_primitive')}",
        f"- Verdict modifier: {karya.get('verdict_modifier')}",
        f"- Rule details: {karya.get('rule_detail', '—')}",
        f"",
        f"## Match Type & Reciprocity",
        f"- Match type: {judgment.get('match_type')} — {judgment.get('match_narrative')}",
        f"- Emotional reciprocity: {judgment.get('emotional_reciprocity')} — {judgment.get('reciprocity_narrative')}",
        f"",
        f"## Bhava Bala — 7th House",
        f"- Net strength: {bhava7.get('net_strength_pct', '—')}% ({bhava7.get('verdict', '—')})",
        f"- Gross: {bhava7.get('gross_strength_pct', '—')}%, afflictions: {len(bhava7.get('malefic_afflictions', []))}",
    ]

    if interference:
        lines += [f"", f"## Third-Party Interference"]
        for itf in interference:
            lines.append(f"- {itf.get('type')}: {itf.get('trigger')}")

    if h2n and 'error' not in h2n:
        lines += [
            f"",
            f"## Horary-to-Natal Shift (NAME THIS NATAL HOUSE in tranche_arc per consistency rule #3)",
            f"- House shift: {h2n.get('shift')} houses",
            f"- Activated natal house: {h2n.get('activated_natal_house')}",
            f"- Flourishing zone: {h2n.get('zone_label')}",
            f"- Zone narrative: {h2n.get('zone_narrative')}",
        ]

    lh = judgment.get('long_horizon') or {}
    if lh.get('is_long_horizon'):
        lines += [
            f"",
            f"## Horizon Boundary (CRITICAL — incorporate into tranche_timeline)",
            f"- Long-horizon keyword matched: \"{lh.get('matched_keyword')}\"",
            f"- The question implies a multi-decade horizon; Prashna's 6-12 month window",
            f"  cannot answer it on its own. Acknowledge this boundary explicitly in",
            f"  tranche_timeline. Frame the verdict as 'current trajectory' rather than",
            f"  'lifelong forecast'. Recommend D-9/D-30 follow-up for the full horizon.",
        ]

    lines += [
        f"",
        f"---",
        f"",
        f"Produce the 3-tranche narrative and 3 action cards now. JSON only, no other text.",
    ]

    return "\n".join(lines)


# -----------------------------------------------------------------
# PHASE 3C — GARBHA AI NARRATIVE
# Reference weighting hardcoded: Prashna Marga > Tajik Neelkanthi > Phaladeepika
# Tonal shift from Vivaha: more tender, less transactional. The querent on a
# fertility query is often emotionally vulnerable — the prompt must hold both
# honesty about negative indicators AND empathy about the stakes.
# -----------------------------------------------------------------



def _build_garbha_user_prompt(judgment: Dict,
                              query_text: Optional[str],
                              cast_meta: Optional[Dict]) -> str:
    """Compose the user prompt for the Garbha narrative. Inlines all judgment data."""

    q = judgment.get('querent_lord', {})
    qs = judgment.get('quesited_lord', {})
    asp = judgment.get('aspect_l1_lt', {})
    nakta = judgment.get('nakta_bridge')
    abhara = judgment.get('abhara_yoga')
    yama = judgment.get('yama_yoga')
    kamboola = judgment.get('kamboola_yoga')
    gada = judgment.get('gada_yoga')
    karya = judgment.get('karya_chain', {})
    strength = judgment.get('strength_scaling', {})
    bhava = judgment.get('bhava_bala_target', {})
    h2n = judgment.get('horary_to_natal', {})
    catalyst = judgment.get('core_catalyst', {})
    eclipse = judgment.get('eclipse_proximity')

    intent = judgment.get('intent', 'conception_possibility')
    target_house = judgment.get('target_house', 5)
    target_role = judgment.get('target_role', '5th — Putra Bhava')
    is_husband_pivot = judgment.get('is_husband_pivot', False)
    is_lineage_query = judgment.get('is_lineage_query', False)
    querent_gender = judgment.get('querent_gender', 'female')
    verdict_modifier = judgment.get('verdict_modifier')

    sphuta_active = judgment.get('sphuta_active')
    sphuta_effect = judgment.get('sphuta_effect')
    mars_5th_risk = judgment.get('mars_5th_risk', False)
    mars_5th_vitality = judgment.get('mars_5th_vitality', False)
    target_cusp_sterile = judgment.get('target_cusp_sterile', False)
    rahu_in_target = judgment.get('rahu_in_target', False)
    ketu_in_target = judgment.get('ketu_in_target', False)

    place = (cast_meta or {}).get('place_name') or "the querent's location"
    when_local = (cast_meta or {}).get('datetime_local_iso', 'now')

    lines = [
        f"# GARBHA PRASHNA — JUDGMENT PACKAGE",
        f"",
        f"## Querent's Question",
        f"\"{query_text or '(no text provided)'}\"",
        f"",
        f"## Querent Profile",
        f"- Gender: {querent_gender}",
        f"- Intent (classified): {intent}",
        f"- Husband-pivot: {is_husband_pivot} (target rotated to 5th-from-7th when True)",
        f"- Lineage-query: {is_lineage_query} (target on 9th house when True)",
        f"",
        f"## Cast Context",
        f"- Cast at: {when_local}",
        f"- Place: {place}",
        f"- Target house: {target_house} ({target_role})",
        f"",
        f"## Verdict (already computed by engine)",
        f"- Verdict: **{judgment.get('verdict')}** — {judgment.get('verdict_text')}",
        f"- Verdict modifier: **{verdict_modifier or 'None'}**",
        f"- Certainty Score: {judgment.get('certainty_score')}% ({judgment.get('certainty_band')})",
        f"- Certainty narrative: {judgment.get('certainty_narrative')}",
    ]

    if verdict_modifier == 'INCONCLUSIVE_RECAST_REQUIRED':
        lines += [
            f"",
            f"## ⚠ INCONCLUSIVE MODIFIER ACTIVE",
            f"- The Moon is void-of-course OR the {target_house}th lord is heavily combust.",
            f"- The narrative MUST frame the verdict as 'cosmic indeterminacy, not denial.'",
            f"- Recommend recasting in 27-28 days as the lunar cycle completes.",
            f"- Clinical disclaimer is mandatory in every tranche.",
        ]

    if intent == 'current_pregnancy_confirmation':
        lines += [
            f"",
            f"## 🏥 MEDICAL DISCLAIMER REQUIRED",
            f"- Intent is current_pregnancy_confirmation.",
            f"- Every tranche must reinforce that Prashna is supplementary to a clinical test.",
            f"- Frame as 'chart suggests direction; only a test confirms' — never 'you should get tested.'",
        ]

    lines += [
        f"",
        f"## Significators (USE synthesis_label as the dominant frame — do not contradict it)",
        f"- **Querent (Lagna Lord)**: {q.get('name')} in {q.get('sign')} (house {q.get('house')}).",
        f"  - Avastha: {q.get('avastha')} — {q.get('condition')}",
        f"  - Degree band: {(q.get('degree_band') or {}).get('band_name', '—')} ({(q.get('degree_band') or {}).get('band_english', '—')})",
        f"  - **Synthesis (use this frame): {q.get('synthesis_label')}** — {q.get('synthesis_narrative')}",
        f"  - Outcome signature: {q.get('outcome')}. Combust: {q.get('is_combust')}.",
        f"- **Quesited ({target_house}th Lord)**: {qs.get('name')} in {qs.get('sign')} (house {qs.get('house')}).",
        f"  - Avastha: {qs.get('avastha')} — {qs.get('condition')}",
        f"  - Degree band: {(qs.get('degree_band') or {}).get('band_name', '—')} ({(qs.get('degree_band') or {}).get('band_english', '—')})",
        f"  - **Synthesis (use this frame): {qs.get('synthesis_label')}** — {qs.get('synthesis_narrative')}",
        f"  - Outcome signature: {qs.get('outcome')}. Combust: {qs.get('is_combust')}. Heavily combust: {qs.get('is_heavily_combust')}.",
        f"",
        f"## Tajik Aspect (Lagna Lord ↔ {target_house}th Lord)",
        f"- Yoga: {asp.get('yoga', 'None')}",
        f"- Within orb: {asp.get('within_orb', False)}",
        f"- Orb: {asp.get('orb_used', '—')}°, separation {asp.get('absolute_separation', '—')}°",
        f"- Aspect narrative: {asp.get('narrative', '—')}",
    ]

    # Sphuta block
    if sphuta_active:
        lines += [
            f"",
            f"## Fertility Coordinate (Sphuta — Parashari biological filter)",
            f"- Type: {sphuta_active.get('sphuta_type', '—').title()} Sphuta "
            f"({'male' if sphuta_active.get('sphuta_type') == 'beeja' else 'female'} fertility point)",
            f"- Computed longitude: {sphuta_active.get('longitude', '—')}° → "
            f"{sphuta_active.get('sign_name', '—')} ({sphuta_active.get('deg_in_sign', '—')}°)",
        ]
        if sphuta_effect:
            lines.append(f"- **Effect:** {sphuta_effect.get('type', '—')} — {sphuta_effect.get('narrative', '—')}")

    # New yogas
    if kamboola:
        lines += [
            f"",
            f"## Kamboola Yoga (Moon as cosmic proxy — overrides primitive NO to YES_WITH_DELAYS)",
            f"- Moon Vimshopaka: {kamboola.get('moon_vimshopaka_score')}/20",
            f"- Narrative: {kamboola.get('narrative')}",
        ]

    if gada:
        lines += [
            f"",
            f"## Gada Yoga (structural compression — forces resolution within 12 months)",
            f"- Kendras occupied: {gada.get('kendras_occupied')}",
            f"- Narrative: {gada.get('narrative')}",
        ]

    if nakta:
        bridge_label = nakta.get('bridge') or '(no qualifying bridge)'
        lines += [
            f"",
            f"## Nakta Bridge (third-planet relay)",
            f"- Bridge planet: {bridge_label}",
            f"- Bridge role: {nakta.get('bridge_role') or '—'}",
            f"- Role narrative: {nakta.get('bridge_role_narrative') or '—'}",
            f"- Narrative: {nakta.get('narrative')}",
        ]
        near = nakta.get('near_misses') or []
        if near:
            lines.append(f"- Near-misses checked:")
            for nm in near:
                lines.append(f"  - {nm.get('narrative', '—')}")

    if abhara:
        lines += [
            f"",
            f"## Abhara Yoga (malefic interference on a valid link)",
            f"- Severity: {abhara.get('severity')}",
            f"- Narrative: {abhara.get('narrative')}",
        ]
        for b in (abhara.get('blockers') or [])[:3]:
            lines.append(f"  - {b.get('malefic')} ({b.get('mode')}): {b.get('narrative')}")

    if yama:
        lines += [
            f"",
            f"## Yama Yoga (midpoint binder — structural / forced conception)",
            f"- Severity: {yama.get('severity')}",
            f"- Narrative: {yama.get('narrative')}",
        ]

    # Garbha-specific structural flags
    lines += [
        f"",
        f"## Garbha Structural Indicators",
    ]
    if target_cusp_sterile:
        lines.append(f"- ⚠ **Sterile cusp (Alpa-Putra):** {target_house}th cusp falls in Gemini/Leo/Virgo/Scorpio. Conception structurally promised but the cellular runway requires preparation.")
    if mars_5th_risk:
        lines.append(f"- 🩸 **Mars in target (risk group — Aries/Cancer/Leo/Libra/Capricorn):** miscarriage / surgical-intervention flag. The narrative must mention medical monitoring.")
    if mars_5th_vitality:
        lines.append(f"- 🟢 **Mars in target (vitality group — Sagittarius/Pisces/etc.):** Mars's heat is tempered. If Jupiter aspects, signals a strong male child (Mangala Karaka).")
    if rahu_in_target:
        lines.append(f"- 🌙 **Rahu in {target_house}th house:** Modern Tajik reading — assisted conception (IVF/IUI/surrogacy). Frame as a viable, modern path, NOT 'demonic affliction.'")
    if ketu_in_target:
        lines.append(f"- 🍃 **Ketu in {target_house}th house:** Spiritual detachment from biological conception — adoption path may be indicated.")
    if not (target_cusp_sterile or mars_5th_risk or mars_5th_vitality or rahu_in_target or ketu_in_target):
        lines.append(f"- No special structural indicators — verdict driven by Karya chain + Sphuta + Bhava Bala only.")

    # Eclipse
    if eclipse:
        lines += [
            f"",
            f"## ⚠ Eclipse Proximity (sincerity hard-capped at 45/100)",
            f"- Eclipse type: {eclipse.get('eclipse_type')}",
            f"- Days from cast: {eclipse.get('days_from_cast')}",
            f"- Axis hit: {eclipse.get('axis_hit')}",
            f"- Narrative: {eclipse.get('narrative')}",
            f"- The tranche_timeline must mention the shadow window and recommend deferring major decisions until it passes.",
        ]

    # Core catalyst + Karya
    lines += [
        f"",
        f"## Core Catalyst",
        f"- Yoga: {catalyst.get('yoga')}",
        f"- Between: {' & '.join(catalyst.get('between', []))}",
        f"- Narrative: {catalyst.get('narrative')}",
        f"",
        f"## Karya Success Chain",
        f"- Positive rules satisfied: {karya.get('positive_satisfied', 0)} / 3",
        f"- Rule 4 fired (combustion/affliction): {karya.get('rule4_fired', False)}",
        f"- Verdict primitive: {karya.get('verdict_primitive')}",
        f"- Verdict modifier: {karya.get('verdict_modifier')}",
        f"- Andha Parivartana: {karya.get('andha_parivartana', False)}",
        f"",
        f"## Bhava Bala — {target_house}th House (progeny axis)",
        f"- Net strength: {bhava.get('net_strength_pct', '—')}% ({bhava.get('verdict', '—')})",
        f"- Sphuta cap applied: {bhava.get('sphuta_cap_applied', False)}",
        f"- Sphuta bonus applied: {bhava.get('sphuta_bonus_applied', False)}",
    ]

    # H2N
    if h2n and 'error' not in h2n:
        lines += [
            f"",
            f"## Horary-to-Natal Shift (NAME THIS NATAL HOUSE in tranche_arc per consistency rule #3)",
            f"- House shift: {h2n.get('shift')} houses",
            f"- Activated natal house: {h2n.get('activated_natal_house')}",
            f"- Flourishing zone: {h2n.get('zone_label')}",
            f"- Zone narrative: {h2n.get('zone_narrative')}",
        ]

    # Long horizon
    lh = judgment.get('long_horizon') or {}
    if lh.get('is_long_horizon'):
        lines += [
            f"",
            f"## Horizon Boundary (CRITICAL — incorporate into tranche_timeline)",
            f"- Long-horizon keyword matched: \"{lh.get('matched_keyword')}\"",
            f"- The question implies a multi-decade horizon; Prashna's 6-12 month window",
            f"  cannot answer it on its own. Acknowledge this boundary explicitly in",
            f"  tranche_timeline. Recommend D-7 Saptamsha follow-up for the full horizon.",
        ]

    lines += [
        f"",
        f"---",
        f"",
        f"Produce the 3-tranche narrative and 3 action cards now. JSON only, no other text.",
    ]

    return "\n".join(lines)


# =================================================================
# PHASE 4D · PUTRA USER PROMPT BUILDER
# =================================================================

def _build_putra_user_prompt(judgment, query_text, cast_meta):
    """
    Dispatcher: routes to the appropriate sub-builder based on the
    judgment's classified intent. Routes:

      child_acute_illness        → _build_putra_illness_prompt
      runaway_estranged_child    → _build_putra_runaway_prompt
      legal_child_custody        → _build_putra_custody_prompt
      child_development_health   → _build_putra_child_dev_prompt
      progeny_capacity (default) → _build_putra_progeny_capacity_prompt
    """
    intent = judgment.get('intent') or 'progeny_capacity'
    if intent == 'child_acute_illness':
        return _build_putra_illness_prompt(judgment, query_text, cast_meta)
    if intent == 'runaway_estranged_child':
        return _build_putra_runaway_prompt(judgment, query_text, cast_meta)
    if intent == 'legal_child_custody':
        return _build_putra_custody_prompt(judgment, query_text, cast_meta)
    if intent == 'child_development_health':
        return _build_putra_child_dev_prompt(judgment, query_text, cast_meta)
    return _build_putra_progeny_capacity_prompt(judgment, query_text, cast_meta)


def _build_putra_illness_prompt(judgment, query_text, cast_meta):
    """Child acute/chronic illness — clinical_protective tone."""
    wb_findings   = judgment.get('findings') or []  # child_wellbeing or illness; we read both
    prognosis     = judgment.get('prognosis')
    fifth_lord    = judgment.get('fifth_lord')
    fifth_lord_house = judgment.get('fifth_lord_house')
    fifth_lord_combust = judgment.get('fifth_lord_combust')
    tenth_lord    = judgment.get('tenth_lord')
    tenth_lord_house = judgment.get('tenth_lord_house')
    tenth_lord_combust = judgment.get('tenth_lord_combust')
    illness_separating = judgment.get('illness_separating')
    illness_applying   = judgment.get('illness_applying')

    querent_lord = judgment.get('querent_lord') or {}
    target_lord  = judgment.get('quesited_lord') or {}
    catalyst     = judgment.get('core_catalyst') or {}
    bhava_target = judgment.get('bhava_bala_target') or {}

    lines = [
        "# Putra Prashna · CHILD ACUTE / CHRONIC ILLNESS (route: child_acute_illness)",
        "",
        "## Cast Context",
        f"- Querent question: \"{query_text or '(not provided)'}\"",
        f"- Place: {(cast_meta or {}).get('place_name', '(not provided)')}",
        f"- Target: 10th — Roga Bhava of the Child (6th from 5th).",
        f"- Operative significator pair: 10th lord ({tenth_lord}) = illness; 5th lord ({fifth_lord}) = the child.",
        "",
        "## CRITICAL FRAMING",
        "- The chart shows TRAJECTORY and PRESSURE WINDOWS — never definite outcomes.",
        "- NEVER predict death or 'no recovery'. If prognosis is grim, frame as 'extended care indicated'.",
        "- ALWAYS direct action to qualified medical professionals. The chart informs; medicine treats.",
        "",
        "## Verdict",
        f"- Verdict state: **{judgment.get('verdict')}**",
        f"- Recovery prognosis band: **{prognosis}**",
        "",
        "## Illness Lord (10th — Roga of the Child)",
        f"- 10th lord: **{tenth_lord}** in house {tenth_lord_house}",
        f"- Combust: {tenth_lord_combust}",
        f"- L10 ↔ L5 relationship: " +
          ("Esrapha (illness separating — recovery indicated)" if illness_separating
           else "applying (illness still pressing)" if illness_applying
           else "no aspect within orb"),
        "",
        "## The Child (5th lord)",
        f"- 5th lord: **{fifth_lord}** in house {fifth_lord_house}",
        f"- Combust: {fifth_lord_combust}",
        "",
        "## Findings",
    ]
    for f in wb_findings:
        prefix = '⚠' if f.get('severity') == 'caveat' else ('✓' if f.get('severity') == 'positive' else '·')
        lines.append(f"  {prefix} **{f.get('name')}**: {f.get('detail')}")

    lines += [
        "",
        "## Significators",
        f"- Lagna lord ({querent_lord.get('name')}): {querent_lord.get('synthesis_label')}",
        "",
        "## Karya / Bhava Bala (10th)",
        f"- 10th Bhava Bala: {bhava_target.get('verdict', '?')} "
        f"(gross {bhava_target.get('gross_strength_pct', 0)}%, net {bhava_target.get('net_strength_pct', 0)}%)",
        "",
        "---",
        "",
        "GUARDRAILS:",
        "- Acknowledge the parent's fear ONCE, briefly. Then move to the chart.",
        "- NEVER predict death. NEVER predict 'no recovery'.",
        "- Action cards point to MEDICAL FOLLOW-THROUGH, never alternative-substitution.",
        "- Sensory remedy is for the PARENT'S equilibrium, never framed as 'cure the child'.",
        "",
        "Produce the JSON now.",
    ]
    return "\n".join(lines)


def _build_putra_runaway_prompt(judgment, query_text, cast_meta):
    """Runaway / estranged child — crisis_supportive tone."""
    return_likelihood  = judgment.get('return_likelihood')
    fifth_lord         = judgment.get('fifth_lord')
    fifth_lord_house   = judgment.get('fifth_lord_house')
    fifth_lord_retro   = judgment.get('fifth_lord_retro')
    distance_to_l1     = judgment.get('distance_to_l1')
    distance_to_cusp   = judgment.get('distance_to_cusp')
    aagaman_findings   = judgment.get('findings') or []

    querent_lord = judgment.get('querent_lord') or {}

    lines = [
        "# Putra Prashna · RUNAWAY / ESTRANGED CHILD · Aagaman (Return) Reading",
        "",
        "## Cast Context",
        f"- Querent question: \"{query_text or '(not provided)'}\"",
        f"- Place: {(cast_meta or {}).get('place_name', '(not provided)')}",
        f"- Target: 8th — Bandhu Bhava of the Child (4th-from-5th = child's home/stability).",
        "",
        "## CRITICAL FRAMING",
        "- This is an Aagaman (return) reading. The classical question: is the child's significator (L5) moving back toward the querent's chart-Lagna or its lord?",
        "- L5 retrograde = the classical RETURN signal. L5 direct = no return signalled at this cast.",
        "- The chart shows DIRECTION, not certainty of reunion. Speak with respect for the child's autonomy.",
        "- NEVER promise a return. NEVER promise reconciliation. Read what the chart shows.",
        "",
        "## Aagaman Reading",
        f"- Verdict: **{judgment.get('verdict')}**",
        f"- Return likelihood band: **{return_likelihood}**",
        "",
        "## The Child's Significator (L5)",
        f"- 5th lord: **{fifth_lord}** in house {fifth_lord_house}",
        f"- L5 motion: **{'retrograde (classical RETURN signal)' if fifth_lord_retro else 'direct (no return signalled)'}**",
        f"- L5 ↔ L1 angular distance: {distance_to_l1}°" if distance_to_l1 is not None else "",
        f"- L5 ↔ Prashna Lagna cusp distance: {distance_to_cusp}°" if distance_to_cusp is not None else "",
        "",
        "## Markers",
    ]
    for f in aagaman_findings:
        prefix = '⚠' if f.get('severity') == 'caveat' else ('✓' if f.get('severity') == 'positive' else '·')
        lines.append(f"  {prefix} **{f.get('name')}**: {f.get('detail')}")

    lines += [
        "",
        "## Significators",
        f"- Lagna lord (you, {querent_lord.get('name')}): {querent_lord.get('synthesis_label')}",
        f"  - {querent_lord.get('synthesis_narrative')}",
        "",
        "---",
        "",
        "GUARDRAILS:",
        "- Speak as a steady adult to a steady adult. No infantilizing.",
        "- Respect the child's autonomy. They are a separate person with their own chart-trajectory.",
        "- Action cards: parent-side stability, open channels without aggressive pursuit, prepare for the form of return the chart actually signals.",
        "- Sensory remedy promises composure, never reunion.",
        "",
        "Produce the JSON now.",
    ]
    return "\n".join(lines)


def _build_putra_custody_prompt(judgment, query_text, cast_meta):
    """Legal child custody — tactical_legal tone."""
    winner       = judgment.get('winner')
    winner_lord  = judgment.get('winner_lord')
    lagna_lord_name = judgment.get('lagna_lord')
    fifth_lord   = judgment.get('fifth_lord')
    seventh_lord = judgment.get('seventh_lord')
    l1_l5_aspect = judgment.get('l1_l5_aspect')
    l1_l5_score  = judgment.get('l1_l5_score')
    l7_l5_aspect = judgment.get('l7_l5_aspect')
    l7_l5_score  = judgment.get('l7_l5_score')

    querent_lord = judgment.get('querent_lord') or {}
    catalyst     = judgment.get('core_catalyst') or {}

    winner_label = {
        'querent':   'the querent (the parent asking)',
        'ex_spouse': 'the other parent',
        'tied':      'NEITHER — both parents read at equivalent strength',
    }.get(winner, 'unclear')

    lines = [
        "# Putra Prashna · LEGAL CHILD CUSTODY (route: legal_child_custody)",
        "",
        "## Cast Context",
        f"- Querent question: \"{query_text or '(not provided)'}\"",
        f"- Place: {(cast_meta or {}).get('place_name', '(not provided)')}",
        f"- Target: 5th — Putra Bhava (the disputed child).",
        "",
        "## Competitive Ithasala Reading",
        f"- L1 (you, {lagna_lord_name}) ↔ L5 ({fifth_lord} = child): **{l1_l5_aspect}** (score +{l1_l5_score})",
        f"- L7 ({seventh_lord} = other parent) ↔ L5: **{l7_l5_aspect}** (score +{l7_l5_score})",
        f"- Positional advantage: **{winner_label}**" + (f" (lord: {winner_lord})" if winner_lord else ""),
        "",
        "## Verdict",
        f"- Verdict state: **{judgment.get('verdict')}**",
        f"- Verdict text: {judgment.get('verdict_text')}",
        "",
        "## Significators",
        f"- Lagna lord ({querent_lord.get('name')}): {querent_lord.get('synthesis_label')}",
        f"- Target lord ({(judgment.get('quesited_lord') or {}).get('name')}): "
        f"{(judgment.get('quesited_lord') or {}).get('synthesis_label')}",
        "",
        "## Core Catalyst",
        f"- {catalyst.get('yoga')}: {catalyst.get('narrative')}",
        "",
        "---",
        "",
        "GUARDRAILS:",
        "- COOL, TACTICAL, CLINICAL. No emotional language about fairness or righteousness.",
        "- This is positional advantage in a Tajik reading — NEVER a prediction of legal certainty.",
        "- Always remind: consult competent legal counsel; the chart informs, never replaces.",
        "- Action cards: timing of filings/negotiations, documentation, when settlement is favored over litigation.",
        "",
        "Produce the JSON now.",
    ]
    return "\n".join(lines)


def _build_putra_child_dev_prompt(judgment, query_text, cast_meta):
    """
    Child development & wellbeing reading. Per Prashna Marga Ch.16:
    the 5th house IS the child; the 6th house IS their speech (2nd-of-5th).
    Mercury (Vak-karaka) is the operative significator.
    """
    querent_lord = judgment.get('querent_lord') or {}
    target_lord  = judgment.get('quesited_lord') or {}
    karya        = judgment.get('karya_chain') or {}
    bhava_target = judgment.get('bhava_bala_target') or {}
    catalyst     = judgment.get('core_catalyst') or {}

    # child_wellbeing_scan data (spread into normalized judgment)
    cw_findings        = judgment.get('findings') or []
    cw_verdict         = judgment.get('verdict')  # may collide with top-level verdict
    fifth_lord         = judgment.get('fifth_lord')
    fifth_lord_house   = judgment.get('fifth_lord_house')
    fifth_lord_combust = judgment.get('fifth_lord_combust')
    malefics_in_5th    = judgment.get('malefics_in_5th') or []
    benefics_in_5th    = judgment.get('benefics_in_5th') or []
    parent_child_aspect = judgment.get('parent_child_aspect')

    # mercury_speech_affliction_check data
    mercury_house         = judgment.get('mercury_house')
    mercury_combust       = judgment.get('mercury_combust')
    mercury_retro         = judgment.get('mercury_retrograde')
    mercury_debilitated   = judgment.get('mercury_debilitated')
    mercury_exalted       = judgment.get('mercury_exalted')
    mercury_in_dushtana   = judgment.get('mercury_in_dushtana')
    malefic_aspects       = judgment.get('malefic_aspects') or []
    benefic_aspects       = judgment.get('benefic_aspects') or []
    mercury_band          = judgment.get('band')

    lines = [
        "# Putra Prashna · CHILD DEVELOPMENT & HEALTH (route: child_development_health)",
        "",
        "## Cast Context",
        f"- Querent question: \"{query_text or '(not provided)'}\"",
        f"- Place: {(cast_meta or {}).get('place_name', '(not provided)')}",
        f"- Target: 6th — Vak Bhava of the Child (2nd from 5th).",
        f"- Operative significator: Mercury (Vak-karaka).",
        "",
        "## CRITICAL FRAMING (Prashna Marga Ch.16)",
        "- The child already exists. This is NOT a fertility or family-size reading.",
        "- The 5th house IS the child themselves (the child's Lagna in this reading).",
        "- The 6th house of the radix IS the child's speech / verbal expression (counted as 2nd-from-5th).",
        "- Mercury (Vak-karaka) is the diagnostic significator for speech and cognition. Jupiter (Putra Karaka) is NOT the primary read here.",
        "",
        "## Verdict",
        f"- Verdict state: **{judgment.get('verdict')}**",
        f"- Verdict text: {judgment.get('verdict_text')}",
        "",
        "## Mercury (Vak-karaka) · Speech Apparatus",
        f"- Mercury house: {mercury_house}",
        f"- Combust: {mercury_combust}  |  Retrograde: {mercury_retro}  |  Debilitated: {mercury_debilitated}  |  Exalted: {mercury_exalted}",
        f"- In Dushtana (6/8/12): {mercury_in_dushtana}",
        f"- Affliction band: **{mercury_band}**",
    ]
    if malefic_aspects:
        lines.append(f"- Malefic aspects to Mercury: " + ", ".join(f"{m['planet']} ({m['yoga']})" for m in malefic_aspects))
    if benefic_aspects:
        lines.append(f"- Benefic aspects to Mercury: " + ", ".join(f"{b['planet']} ({b['yoga']})" for b in benefic_aspects))

    lines += [
        "",
        "## The Child Themselves · 5th-Lord & 5th-House",
        f"- 5th lord ({fifth_lord}) is in the {fifth_lord_house}th house" if fifth_lord_house else f"- 5th lord: {fifth_lord}",
        f"- 5th lord combust: {fifth_lord_combust}",
        f"- Malefics in 5th: {', '.join(malefics_in_5th) if malefics_in_5th else 'none'}",
        f"- Benefics in 5th: {', '.join(benefics_in_5th) if benefics_in_5th else 'none'}",
        f"- Parent ↔ Child aspect (Lagna lord ↔ 5L): {parent_child_aspect or 'none within orb'}",
    ]
    if cw_findings:
        lines.append("- Wellbeing findings:")
        for f in cw_findings:
            prefix = '⚠' if f.get('severity') == 'caveat' else ('✓' if f.get('severity') == 'positive' else '·')
            lines.append(f"  {prefix} **{f.get('name')}**: {f.get('detail')}")

    lines += [
        "",
        "## Significators (orchestrator)",
        f"- Lagna lord ({querent_lord.get('name')}): {querent_lord.get('synthesis_label')}",
        f"  - {querent_lord.get('synthesis_narrative')}",
        f"- Target lord ({target_lord.get('name')}): {target_lord.get('synthesis_label')}",
        "",
        "## Karya & Bhava Bala (6th house · the speech apparatus)",
        f"- Karya: {karya.get('positive_satisfied', 0)} / 3 satisfied (primitive: {karya.get('verdict_primitive')})",
        f"- 6th Bhava Bala: {bhava_target.get('verdict', '?')} "
        f"(gross {bhava_target.get('gross_strength_pct', 0)}%, net {bhava_target.get('net_strength_pct', 0)}%)",
        "",
        "---",
        "",
        "ABSOLUTE GUARDRAILS:",
        "- DO NOT mention 'family size', 'how many children', 'fertility', 'conception', 'IVF', 'future progeny'.",
        "- The child IS HERE. The query is about their development, not about whether they will exist.",
        "- Be warm but clinical. Diagnostic clarity, not platitudes.",
        "- Action cards point to CONCRETE developmental support: speech therapy, paediatric assessment, structured cognitive practice.",
        "- NEVER predict outcomes definitively. Describe architectures, tendencies, supports, friction.",
        "",
        "Produce the JSON now.",
    ]
    return "\n".join(lines)


def _build_putra_progeny_capacity_prompt(judgment, query_text, cast_meta):
    """Long-horizon progeny capacity reading (the original Putra builder)."""
    yogas             = judgment.get('yogas') or []
    family_size_band  = judgment.get('family_size_band')
    band_narrative    = judgment.get('band_narrative')
    fifth_lord        = judgment.get('fifth_lord')
    jupiter_house     = judgment.get('jupiter_house')
    d7_verdict        = judgment.get('d7_verdict')
    d7_narrative      = judgment.get('d7_narrative')
    lagna_d7_sign     = judgment.get('lagna_d7_sign')
    fifth_lord_d7_sign = judgment.get('fifth_lord_d7_sign')
    jupiter_d7_sign   = judgment.get('jupiter_d7_sign')
    fertile_count     = judgment.get('fertile_count')
    barren_count      = judgment.get('barren_count')

    querent_lord = judgment.get('querent_lord') or {}
    bhava_target = judgment.get('bhava_bala_target') or {}
    catalyst     = judgment.get('core_catalyst') or {}
    karya        = judgment.get('karya_chain') or {}

    lines = [
        "# Putra Prashna · Long-Horizon Progeny Capacity Reading",
        "",
        "## Cast Context",
        f"- Querent question: \"{query_text or '(not provided)'}\"",
        f"- Place: {(cast_meta or {}).get('place_name', '(not provided)')}",
        f"- Target: 5th — Putra Bhava (Long-Horizon)",
        "",
        "## Verdict",
        f"- Verdict state: **{judgment.get('verdict')}**",
        f"- Verdict text: {judgment.get('verdict_text')}",
        f"- Family-size band: **{family_size_band}**",
        f"- Band narrative: {band_narrative}",
        "",
        "## Putra Yoga Catalogue",
        f"- 5th lord: {fifth_lord}",
        f"- Jupiter (Putra Karaka) house: {jupiter_house}",
        f"- Yogas fired: {len(yogas)}",
    ]
    for y in yogas:
        prefix = '⚠' if y.get('is_caveat') else '✓'
        lines.append(f"  {prefix} **{y.get('name')}**: {y.get('detail')}")
    if not yogas:
        lines.append("  (no classical Putra yogas fired — frame restrictively but not fatalistically)")

    lines += [
        "",
        "## Saptamsha (D7) Varga Anchor",
        f"- D7 verdict: **{d7_verdict}**",
        f"- D7 narrative: {d7_narrative}",
        f"- Lagna in D7: {lagna_d7_sign}  |  5L ({fifth_lord}) in D7: {fifth_lord_d7_sign}  |  Jupiter in D7: {jupiter_d7_sign}",
        f"- Fertile-sign indicators: {fertile_count}/3  |  Barren-sign indicators: {barren_count}/3",
        "",
        "## Significator Conditions",
        f"- Lagna lord ({querent_lord.get('name')}): synthesis_label = **{querent_lord.get('synthesis_label')}**",
        f"  - Synthesis: {querent_lord.get('synthesis_narrative')}",
        "",
        "## Bhava Bala (5th)",
        f"- {bhava_target.get('strength_label', 'N/A')} ({bhava_target.get('pct', 0)}%) — {bhava_target.get('narrative', '')}",
        "",
        "## Core Catalyst",
        f"- Yoga: {catalyst.get('yoga')}",
        f"- Between: {' & '.join(catalyst.get('between', []))}",
        f"- Narrative: {catalyst.get('narrative')}",
        "",
        "## Karya Chain",
        f"- Positive rules satisfied: {karya.get('positive_satisfied', 0)} / 3",
        f"- Verdict primitive: {karya.get('verdict_primitive')}",
        "",
        "---",
        "",
        "GUARDRAIL: This is the LONG-HORIZON reading. Never predict a specific number of children.",
        "Frame in capacity, tendency, and lifestyle alignment. Distinguish from Garbha (immediate cycle).",
        "Produce the 3-tranche narrative and 3 action cards now. JSON only, no other text.",
    ]
    return "\n".join(lines)


# =================================================================
# PHASE 4D · ANYA-SAMBANDHA USER PROMPT BUILDER
# =================================================================

def _build_anya_sambandha_user_prompt(judgment, query_text, cast_meta):
    """Unconventional / hidden alliances prompt."""
    signatures      = judgment.get('signatures') or []
    signature_count = judgment.get('count', 0)
    activations     = judgment.get('activations') or []
    axes_hit        = judgment.get('axes_hit') or []
    rahu_house      = judgment.get('rahu_house')
    ketu_house      = judgment.get('ketu_house')
    nakta_bridge    = judgment.get('nakta_bridge')
    abhara_yoga     = judgment.get('abhara_yoga')

    querent_lord = judgment.get('querent_lord') or {}
    quesited_lord = judgment.get('quesited_lord') or {}
    catalyst     = judgment.get('core_catalyst') or {}

    lines = [
        "# Anya-Sambandha Prashna · Unconventional / Hidden Alliances Reading",
        "",
        "## Cast Context",
        f"- Querent question: \"{query_text or '(not provided)'}\"",
        f"- Place: {(cast_meta or {}).get('place_name', '(not provided)')}",
        f"- Target: 7th — Yuvati Bhava (with 12th-house pivots)",
        "",
        "## Verdict",
        f"- Verdict state: **{judgment.get('verdict')}**",
        f"- Verdict text: {judgment.get('verdict_text')}",
        "",
        f"## Hidden-Relationship Signatures ({signature_count} detected)",
    ]
    if signatures:
        for s in signatures:
            lines.append(f"  • **{s.get('name')}**: {s.get('detail')}")
    else:
        lines.append("  (no hidden signatures — partnership terrain operates overtly, if at all)")

    lines += [
        "",
        "## Node-Axis Activation",
        f"- Rahu house: {rahu_house}  |  Ketu house: {ketu_house}",
        f"- Active axes: {axes_hit if axes_hit else 'none'}",
        f"- Activations fired: {len(activations)}",
    ]
    for a in activations:
        lines.append(f"  • **{a.get('name')}**: {a.get('detail')}")

    lines += [
        "",
        "## Tajik Connection",
        f"- Lagna lord ({querent_lord.get('name')}): synthesis_label = **{querent_lord.get('synthesis_label')}**",
        f"- Target lord ({quesited_lord.get('name')}): synthesis_label = **{quesited_lord.get('synthesis_label')}**",
        f"- Nakta bridge: {('via ' + nakta_bridge['bridge']) if nakta_bridge and nakta_bridge.get('bridge') else 'none'}",
        f"- Abhara yoga (malefic friction): {'present' if abhara_yoga else 'absent'}",
        "",
        "## Core Catalyst",
        f"- Yoga: {catalyst.get('yoga')}",
        f"- Narrative: {catalyst.get('narrative')}",
        "",
        "---",
        "",
        "GUARDRAIL: ABSOLUTE CLINICAL DISTANCE. NO MORALISING.",
        "Report what the chart says about the dynamics — do NOT advise on whether to pursue.",
        "Use vocabulary like 'signature', 'marker', 'energetic load' — NEVER 'wrong', 'sinful', 'should not'.",
        "Tactical truth only. Produce the JSON now.",
    ]
    return "\n".join(lines)


# =================================================================
# PHASE 4D · KINSHIP & ALLIANCES USER PROMPT BUILDER
# =================================================================

def _ordinal_pretty(n):
    if n is None: return ''
    if 10 <= n % 100 <= 20: return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


def _build_kinship_user_prompt(judgment, query_text, cast_meta):
    """Sahaja (siblings) + Mitra (networks) prompt."""
    sibling      = judgment.get('sibling') or {}
    networks     = judgment.get('networks') or {}
    aggregated   = judgment.get('aggregated_verdict')
    sibling_bridge = judgment.get('sibling_bridge') or {}
    network_bridge = judgment.get('network_bridge') or {}
    has_sibling_bridge = judgment.get('has_sibling_bridge')
    has_network_bridge = judgment.get('has_network_bridge')

    querent_lord = judgment.get('querent_lord') or {}

    lines = [
        "# Kinship & Alliances Prashna · Sahaja + Mitra Reading",
        "",
        "## Cast Context",
        f"- Querent question: \"{query_text or '(not provided)'}\"",
        f"- Place: {(cast_meta or {}).get('place_name', '(not provided)')}",
        f"- Target: 3rd / 11th — Sahaja Bhava + Labha Bhava",
        "",
        "## Aggregated Verdict",
        f"- Verdict state: **{judgment.get('verdict')}**",
        f"- Verdict text: {judgment.get('verdict_text')}",
        f"- Aggregated network posture: **{aggregated}**",
        "",
        "## Sibling Axis (3rd · Sahaja Bhava)",
        f"- 3rd lord: **{sibling.get('lord')}** in {sibling.get('lord_house')}{_ordinal_pretty(sibling.get('lord_house'))} house",
        f"- Naisargika relationship to Lagna lord: {sibling.get('friendship')}",
        f"- Aspect quality with Lagna lord: {sibling.get('aspect_quality')}",
        f"- Combust: {sibling.get('is_combust')}",
        f"- Verdict: **{sibling.get('verdict')}**",
        "",
        "## Network Axis (11th · Labha Bhava)",
        f"- 11th lord: **{networks.get('lord')}** in {networks.get('lord_house')}{_ordinal_pretty(networks.get('lord_house'))} house",
        f"- Naisargika relationship to Lagna lord: {networks.get('friendship')}",
        f"- Aspect quality with Lagna lord: {networks.get('aspect_quality')}",
        f"- Combust: {networks.get('is_combust')}",
        f"- Verdict: **{networks.get('verdict')}**",
        "",
        "## Nakta Bridge Relay",
        f"- Sibling axis bridged via intermediary: {has_sibling_bridge}",
    ]
    if has_sibling_bridge:
        lines.append(f"  • Bridge planet: **{sibling_bridge.get('bridge')}** ({sibling_bridge.get('bridge_role')})")
    lines.append(f"- Network axis bridged via intermediary: {has_network_bridge}")
    if has_network_bridge:
        lines.append(f"  • Bridge planet: **{network_bridge.get('bridge')}** ({network_bridge.get('bridge_role')})")

    lines += [
        "",
        "## Significator Conditions",
        f"- Lagna lord ({querent_lord.get('name')}): synthesis_label = **{querent_lord.get('synthesis_label')}**",
        f"  - Synthesis: {querent_lord.get('synthesis_narrative')}",
        "",
        "---",
        "",
        "GUARDRAIL: NETWORK STRATEGY reading. Use modern frames (siblings, professional network,",
        "mentors, close friends). Avoid antique 'brothers and well-wishers' language.",
        "Tell the querent who to invest in and who to detach from, with chart citations.",
        "Produce the JSON now.",
    ]
    return "\n".join(lines)







# =================================================================
# USER PROMPT BUILDERS REGISTRY
# =================================================================
# Maps topic_id → builder function. Each builder accepts
#   (normalized_judgment, query_text, cast_meta)
# and returns a string user prompt.
#
# Adding a new sub-module = define _build_<topic>_user_prompt() and
# register it here. No route changes.
# =================================================================

USER_PROMPT_BUILDERS = {
    "vivaha":         _build_vivaha_user_prompt,
    "garbha":         _build_garbha_user_prompt,
    # Phase 4D additions:
    "putra":          _build_putra_user_prompt,
    "anya_sambandha": _build_anya_sambandha_user_prompt,
    "kinship":        _build_kinship_user_prompt,
    # "karma":          _build_karma_user_prompt,
    # "sammana":        _build_sammana_user_prompt,
    # "pravasa":        _build_pravasa_user_prompt,
    # "shatru":         _build_shatru_user_prompt,
    # "vivada":         _build_vivada_user_prompt,
    # "sangrama":       _build_sangrama_user_prompt,
    # "dhana":          _build_dhana_user_prompt,
    # "vyapara":        _build_vyapara_user_prompt,
    # "bhumi_labha":    _build_bhumi_labha_user_prompt,
    # "roga":           _build_roga_user_prompt,
    # "daiva_roga":     _build_daiva_roga_user_prompt,
    # "confinement":    _build_confinement_user_prompt,
}


# =================================================================
# DISPATCHER
# =================================================================

class NarrativeError(Exception):
    """Raised by build_narrative_prompts / generate_narrative on misconfiguration."""
    pass


def build_narrative_prompts(topic_id: str,
                             judgment: Dict,
                             query_text: Optional[str] = None,
                             cast_meta: Optional[Dict] = None,
                             topic_inputs: Optional[Dict] = None):
    """
    Returns (system_prompt, user_prompt) for the given topic.

    Reads the narrative tone from PRASHNA_TOPICS[topic_id] and pairs
    the matching system prompt with the registered user-prompt builder.

    Raises NarrativeError if:
      - topic_id is not in PRASHNA_TOPICS
      - the topic's narrative_tone is not in NARRATIVE_TONES
      - no user-prompt builder is registered for the topic_id
    """
    if topic_id not in PRASHNA_TOPICS:
        raise NarrativeError(
            f"Unknown topic_id \'{topic_id}\'. Registered: {sorted(PRASHNA_TOPICS)}"
        )

    spec = PRASHNA_TOPICS[topic_id]
    # Intent-routed topics (e.g. putra) put the route-resolved tone in the
    # judgment itself. Prefer that; fall back to the spec default.
    tone = judgment.get("narrative_tone") or spec.get("narrative_tone")
    if tone not in NARRATIVE_TONES:
        raise NarrativeError(
            f"Topic \'{topic_id}\' declares narrative_tone=\'{tone}\' "
            f"but no system prompt is registered for this tone."
        )

    builder = USER_PROMPT_BUILDERS.get(topic_id)
    if builder is None:
        raise NarrativeError(
            f"No user-prompt builder registered for topic \'{topic_id}\'. "
            f"Add an entry to USER_PROMPT_BUILDERS."
        )

    normalized = _normalize_judgment_for_prompt(judgment, topic_id, topic_inputs)
    system_prompt = NARRATIVE_TONES[tone]
    user_prompt = builder(normalized, query_text, cast_meta)
    return system_prompt, user_prompt


# =================================================================
# END-TO-END GENERATOR
# =================================================================
# One-call wrapper: builds prompts, invokes Anthropic, parses JSON.
# The route layer just passes its anthropic client + the inputs.
# =================================================================

NARRATIVE_REQUIRED_KEYS = {
    "tranche_arc",      "tranche_strategy", "tranche_timeline",
    "platinum_rule",    "friction_gate",    "sensory_remedy",
}


def generate_narrative(anthropic_client,
                        topic_id: str,
                        judgment: Dict,
                        query_text: Optional[str] = None,
                        cast_meta: Optional[Dict] = None,
                        topic_inputs: Optional[Dict] = None,
                        max_tokens: int = 2000) -> Dict:
    """
    Build prompts, call the LLM, return parsed narrative dict + usage.

    Returns: { narrative, model, usage } — to be wrapped in route response.
    Raises NarrativeError on prompt/registry issues; lets LLM exceptions
    bubble up to the caller for HTTP-aware error wrapping.
    """
    system_prompt, user_prompt = build_narrative_prompts(
        topic_id, judgment, query_text, cast_meta, topic_inputs
    )

    msg = anthropic_client.messages.create(
        model=PRASHNA_AI_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(
        getattr(b, "text", "") for b in msg.content
        if getattr(b, "type", None) == "text"
    )

    # Strip accidental markdown fences
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    cleaned = cleaned.strip()

    try:
        parsed = _json.loads(cleaned)
    except _json.JSONDecodeError as exc:
        raise NarrativeError(
            f"LLM returned non-JSON: {str(exc)[:200]}. "
            f"First 200 chars of response: {raw_text[:200]}"
        )

    missing = NARRATIVE_REQUIRED_KEYS - set(parsed.keys())
    if missing:
        raise NarrativeError(
            f"LLM response missing required keys: {sorted(missing)}. "
            f"Got: {sorted(parsed.keys())}"
        )

    return {
        "narrative": parsed,
        "model":     PRASHNA_AI_MODEL,
        "usage": {
            "input_tokens":  getattr(msg.usage, "input_tokens", None),
            "output_tokens": getattr(msg.usage, "output_tokens", None),
        },
    }


# =================================================================
# END OF PHASE 4C — prashna_narratives.py
# =================================================================
