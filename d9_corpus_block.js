// D9 corpus, generated from D9-corpus-FINAL.xlsx by build_d9_corpus.py.
// Keyed off the graha and dignity_label COLUMNS, never off row_id: the
// row_id underscores the space in 'Own Sign', so a join-built key drops
// tier 2 for all nine grahas, silently.
const D9_RASHI_CORPUS = Object.freeze({
  "Jupiter": {
    "Debilitated": "Higher guidance faces fundamental compromise; the wisdom and moral vision expressed in {sign} struggle against excessive materialism, cynicism, and restrictive doubt.",
    "Enemy": "Higher wisdom encounters friction and ideological resistance; the guidance and optimism expressed in {sign} must be maintained against underlying cynicism or rigid debate.",
    "Exalted": "Higher wisdom aligns with profound moral expansion; the guidance, faith, and ethical nobility expressed in {sign} operates with unshakeable benevolence.",
    "Friend": "Higher wisdom finds receptive support; the guidance and expansive vision expressed in {sign} operates with constructive alignment and shared optimism.",
    "Moolatrikona": "Philosophical vision operates with purposeful dharma; the wisdom and righteous counsel expressed in {sign} flows directly from higher law and principled duty.",
    "Neutral": "Higher wisdom functions with measured balance; the guidance and philosophical perspective expressed in {sign} operates through steady, pragmatic observation.",
    "Own Sign": "Higher guidance rests comfortably in its natural domain; the wisdom and expansive optimism expressed in {sign} flows with unforced philosophical grace."
  },
  "Ketu": {
    "Debilitated": "Spiritual discernment faces fundamental compromise; the detachment, intuition, and subtle discrimination expressed in {sign} struggle against disorientation, phantom fears, and persistent dissatisfaction.",
    "Enemy": "Spiritual discernment encounters friction and internal resistance; the detachment, intuition, and urge for independence expressed in {sign} must be maintained against underlying agitation and doubt.",
    "Exalted": "Transcendent insight aligns with supreme spiritual clarity; the detachment, keen intuition, and liberation expressed in {sign} operate with profound, penetrating wisdom.",
    "Friend": "Spiritual discernment finds receptive support; the detachment, intuition, and penetrating insight expressed in {sign} operate with constructive alignment and quiet focus.",
    "Moolatrikona": "Spiritual insight operates with purposeful detachment; the intuition, research capability, and subtle perception expressed in {sign} flow directly from innate mastery and quiet conviction.",
    "Neutral": "Spiritual discernment functions with measured balance; the detachment, intuition, and internal focus expressed in {sign} operate through steady, objective observation.",
    "Own Sign": "Spiritual discernment rests comfortably in its natural domain; the detachment, intuitive depth, and internal focus expressed in {sign} flow with unforced ease."
  },
  "Mars": {
    "Debilitated": "Executive vigor faces fundamental compromise; the courage and decisive action expressed in {sign} struggle against emotional reactivity and suppressed frustration.",
    "Enemy": "Executive vigor encounters friction and conflict; the drive and initiative expressed in {sign} must be maintained through conscious discipline against underlying frustration.",
    "Exalted": "Constructive drive aligns with disciplined strategy; the courage and executive force expressed in {sign} operates with purposeful, controlled mastery.",
    "Friend": "Executive vigor finds receptive support; the courage and active drive expressed in {sign} operates with constructive alignment and shared motivation.",
    "Moolatrikona": "Vital drive operates with purposeful initiative; the courage and executive force expressed in {sign} flows directly from focused resolve and active duty.",
    "Neutral": "Executive vigor functions with measured balance; the drive and determination expressed in {sign} operates through practical adaptability.",
    "Own Sign": "Executive vigor rests comfortably in its natural domain; the drive and determination expressed in {sign} flows with unforced physical confidence."
  },
  "Mercury": {
    "Debilitated": "Intellectual discernment faces fundamental compromise; the logic and analytical precision expressed in {sign} struggle against idealization, vagueness, and unreliable discrimination.",
    "Enemy": "Intellectual discernment encounters friction and mental resistance; the logic and communicative clarity expressed in {sign} must be maintained against underlying overthinking and scattered focus.",
    "Exalted": "Intellectual discernment aligns with supreme analytical clarity; the logic and communicative precision expressed in {sign} operates with flawless objective mastery.",
    "Friend": "Intellectual discernment finds receptive support; the logic and communicative ability expressed in {sign} operates with constructive alignment and fluid exchange.",
    "Moolatrikona": "Analytical discernment operates with purposeful efficiency; the intellect and communicative skill expressed in {sign} flows directly from practical logic and systematic duty.",
    "Neutral": "Intellectual discernment functions with measured balance; the logic and communicative ability expressed in {sign} operates through steady, pragmatic observation.",
    "Own Sign": "Intellectual agility rests comfortably in its natural domain; the curiosity and expressive skill expressed in {sign} flows with unforced mental adaptability."
  },
  "Moon": {
    "Debilitated": "Emotional consciousness faces fundamental vulnerability; the sensitivity and intuitive care expressed in {sign} struggle against underlying anxiety and mental turmoil.",
    "Enemy": "Emotional consciousness encounters friction and inner discomfort; the sensitivity and intuitive care expressed in {sign} must be maintained against underlying mental restlessness.",
    "Exalted": "Emotional equilibrium aligns with profound inner security; the sensitivity and nurturing capacity expressed in {sign} stems from unshakeable psychological peace.",
    "Friend": "Emotional consciousness finds receptive support; the sensitivity and intuitive care expressed in {sign} operates with natural mental harmony.",
    "Moolatrikona": "Inner stability operates with purposeful grace; the nurturing capacity and mental peace expressed in {sign} flows directly from an inherently centered mind.",
    "Neutral": "Emotional consciousness functions with measured balance; the sensitivity and intuitive care expressed in {sign} operates through steady adaptability.",
    "Own Sign": "Emotional consciousness rests comfortably in its natural domain; the nurturing capacity and intuitive care expressed in {sign} flows with unforced ease."
  },
  "Rahu": {
    "Debilitated": "Unconventional drive faces fundamental compromise; the ambition, innovation, and desires expressed in {sign} struggle against overwhelming illusion, anxiety, and chaotic obsession.",
    "Enemy": "Unconventional drive encounters friction and internal resistance; the ambition, innovation, and quest for growth expressed in {sign} must be maintained against underlying restlessness and agitation.",
    "Exalted": "Worldly ambition aligns with extraordinary amplification; the innovation, magnetic drive, and obsession expressed in {sign} operate with breakthrough visionary power.",
    "Friend": "Unconventional drive finds receptive support; the ambition, innovation, and worldly desire expressed in {sign} operate with constructive alignment and strategic momentum.",
    "Moolatrikona": "Worldly ambition operates with purposeful acceleration; the innovation, unconventional drive, and material focus expressed in {sign} flow directly from sharp strategic desire.",
    "Neutral": "Unconventional drive functions with measured balance; the ambition, innovation, and worldly desire expressed in {sign} operate through steady, pragmatic experimentation.",
    "Own Sign": "Unconventional drive rests comfortably in its natural domain; the ambition, strategic disruption, and desire expressed in {sign} flow with unforced innovative sharpness."
  },
  "Saturn": {
    "Debilitated": "Structural endurance faces fundamental compromise; the discipline, patience, and long-term vision expressed in {sign} struggle against impulsiveness, frustration, and misdirected force.",
    "Enemy": "Structural endurance encounters friction and underlying resistance; the discipline and perseverance expressed in {sign} must be maintained through deliberate effort against internal fatigue.",
    "Exalted": "Enduring discipline aligns with ultimate balance; the perseverance, structural integrity, and patience expressed in {sign} operate with noble, objective authority.",
    "Friend": "Structural endurance finds receptive support; the discipline, patience, and realistic focus expressed in {sign} operate with constructive alignment and strategic order.",
    "Moolatrikona": "Systemic responsibility operates with purposeful service; the discipline, duty, and endurance expressed in {sign} flow directly from collective order and structured effort.",
    "Neutral": "Structural endurance functions with measured balance; the discipline, patience, and caution expressed in {sign} operate through steady, pragmatic persistence.",
    "Own Sign": "Structural endurance rests comfortably in its natural domain; the patience, responsibility, and discipline expressed in {sign} flow with unforced stamina."
  },
  "Sun": {
    "Debilitated": "Essential authority faces fundamental compromise; the confidence and radiance expressed in {sign} struggles against diminished self-worth and over-reliance on external validation.",
    "Enemy": "Essential authority encounters friction and resistance; the confidence and leadership expressed in {sign} must be maintained through conscious effort against underlying strain.",
    "Exalted": "Core authority aligns with true soul purpose; the radiance and leadership expressed in {sign} stems from authentic self-certainty.",
    "Friend": "Essential authority finds receptive backing; the confidence and vitality expressed in {sign} operates with harmonious support and shared purpose.",
    "Moolatrikona": "Natural authority operates with purposeful command; the leadership expressed in {sign} flows directly from an innate sense of duty and sovereign alignment.",
    "Neutral": "Essential authority functions with measured balance; the confidence and vitality expressed in {sign} operates through steady adaptability.",
    "Own Sign": "Sovereign identity rests comfortably in its natural domain; the confidence and authority expressed in {sign} flows with unforced self-assurance."
  },
  "Venus": {
    "Debilitated": "Harmonious grace faces fundamental compromise; the relational capacity and self-worth expressed in {sign} struggle against hyper-criticism, perfectionism, and emotional anxiety.",
    "Enemy": "Harmonious grace encounters friction and relational tension; the desire for connection and artistic expression in {sign} must be maintained against underlying austerity or conflict.",
    "Exalted": "Refined devotion aligns with unconditional harmony; the grace, aesthetic beauty, and relational capacity expressed in {sign} operates with sublime, transcendent purity.",
    "Friend": "Harmonious grace finds receptive support; the relational capacity and aesthetic appreciation expressed in {sign} operate with pleasant alignment and mutual goodwill.",
    "Moolatrikona": "Aesthetic refinement operates with purposeful balance; the harmony, value, and relational capacity expressed in {sign} flow directly from social duty and balanced order.",
    "Neutral": "Harmonious grace functions with measured balance; the relational capacity and aesthetic expression in {sign} operate through steady, pragmatic adjustment.",
    "Own Sign": "Harmonious grace rests comfortably in its natural domain; the artistic discernment and relational equilibrium expressed in {sign} flow with unforced charm."
  }
});
const VARGA_SHIFT_CORPUS = Object.freeze({
  "Jupiter": {
    "held": "Outer ethical stance fully reflects inner belief; wisdom and guidance expressed outwardly are exactly held within.",
    "stronger": "Inner wisdom quietly exceeds outer expression; moral clarity, faith, and philosophical depth reveal greater strength over time.",
    "weaker": "Outward optimism overstates inner conviction; moral confidence and guidance weaken when tested by real-world adversity."
  },
  "Ketu": {
    "held": "Outer detachment fully reflects inner stillness; intuitive mastery and independence shown outwardly are exactly held within.",
    "stronger": "Inner detachment and intuitive perception quietly exceed outer appearance; spiritual insight and discrimination run much deeper than seen.",
    "weaker": "Outward detachment overstates inner liberation; apparent independence and dispassion mask underlying confusion or dissatisfaction."
  },
  "Mars": {
    "held": "Outward drive fully reflects inner resolve; courage and executive action shown outwardly are precisely held within.",
    "stronger": "Inner courage quietly exceeds outer expression; drive, stamina, and tactical resolve grow stronger when challenges escalate.",
    "weaker": "Outward showing overstates the inner resource; initiative starts well and thins under sustained pressure."
  },
  "Mercury": {
    "held": "Outer communication fully reflects inner intellect; analytical clarity and logic expressed outwardly are exactly held within.",
    "stronger": "Inner intellectual acuity quietly exceeds outer articulation; strategic discernment and analytical depth run much deeper than displayed.",
    "weaker": "Outward articulateness overstates inner logic; intellectual confidence starts well but loses coherence under rigorous challenge."
  },
  "Moon": {
    "held": "Outer emotional demeanor fully reflects inner mind; sensitivity and psychological state shown outwardly match what is held within.",
    "stronger": "Inner emotional resilience quietly exceeds outer expression; peace of mind and psychological depth prove far steadier than initially seen.",
    "weaker": "Outward composure overstates inner calm; emotional stability and mental comfort thin under sustained personal stress."
  },
  "Rahu": {
    "held": "Outer ambition fully reflects inner drive; hunger for growth and worldly innovation shown outwardly match what is held within.",
    "stronger": "Inner strategic ambition quietly exceeds outer projection; drive, hunger for mastery, and visionary reach expand over time.",
    "weaker": "Outward boldness overstates inner drive; ambitious claims and innovative posturing unravel under sustained accountability."
  },
  "Saturn": {
    "held": "Outer discipline fully reflects inner stamina; perseverance and sense of duty expressed outwardly are exactly held within.",
    "stronger": "Inner endurance and discipline quietly exceed outer appearance; structural stamina and patience prove far stronger over time.",
    "weaker": "Outward composure overstates inner stamina; discipline and patience wear down under long-term pressure."
  },
  "Sun": {
    "held": "Outer authority fully reflects inner core; self-certainty and sovereignty expressed outwardly are exactly held within.",
    "stronger": "Inner conviction quietly exceeds outer presentation; true self-certainty and personal authority reveal greater depth when put to the test.",
    "weaker": "Outward confidence overstates the inner core; leadership and authority show initial promise but falter under true personal scrutiny."
  },
  "Venus": {
    "held": "Outer warmth and aesthetic expression fully reflect inner values; harmony and relational depth shown outwardly are exactly held within.",
    "stronger": "Inner capacity for devotion and refinement exceeds outer expression; relational grace and artistic value run much deeper than shown.",
    "weaker": "Outward charm overstates inner satisfaction; relational grace and value commitments prove difficult to sustain when tested."
  }
});
const VARGOTTAMA_NOTE = "Absolute alignment between internal capacity and external reality; the planetary energy functions with pristine consistency, unyielding structural strength, and seamless continuity.";

// Runtime completeness guard. A silently short table is the defect this
// whole ticket exists to stop, so absence fails loudly at load.
(function d9CorpusGuard(){
  const G=["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"];
  const T=["Exalted", "Moolatrikona", "Own Sign", "Friend", "Neutral", "Enemy", "Debilitated"];
  const D=["stronger", "held", "weaker"];
  const miss=[];
  G.forEach(g=>{T.forEach(t=>{if(!(D9_RASHI_CORPUS[g]||{})[t])miss.push('D9_RASHI_CORPUS.'+g+'.'+t);});
               D.forEach(d=>{if(!(VARGA_SHIFT_CORPUS[g]||{})[d])miss.push('VARGA_SHIFT_CORPUS.'+g+'.'+d);});});
  if(!VARGOTTAMA_NOTE)miss.push('VARGOTTAMA_NOTE');
  if(miss.length)throw new Error('D9 corpus incomplete: '+miss.join(', '));
})();
