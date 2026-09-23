# Rules Applied: 02-readme

## Pass 1: Vocabulary replacements
- "comprehensive" (x2) -> removed
- "robust" (x2) -> removed
- "seamlessly"/"seamless" (x2) -> "auto-detects" / removed
- "pivotal" -> removed
- "navigate" (figurative) -> removed
- "diverse array" -> specific list (YAML, env vars, Consul, etcd)
- "leveraging" -> removed
- "meticulously designed" -> removed
- "fostering" (x2) -> removed
- "embark on your journey" -> "quick start"
- "delve into" -> "see"
- "crucial" -> removed
- "landscape" -> removed
- "enhance" -> removed
- "encompasses" -> removed
- "holistic" -> removed

## Pass 2: Structural patterns fixed
- Generic opener in "Why ConfigManager?" -> deleted
- Inline-header list (bold + colon) -> converted to terse bullet list
- Negative parallelism ("Not only...but also") -> deleted
- Promotional tone throughout -> flattened to factual
- "Additionally" sentence start -> merged into preceding paragraph
- Excessive bold in feature list -> removed

## Pass 3: Voice transformation
- Added practical code example (schema + usage)
- Parenthetical humor ("catches bad config at startup, not at 3am")
- Direct address ("your app")
- Terse feature descriptions (one line each)
- Specific named tools (Consul, etcd) instead of generic "remote services"
- Contributing section reduced to one line (it's a README, not a speech)
- Conversational tone ("is annoying", "catch problems early")

## Pass 5: Verification
- AI vocabulary density: 0 -- PASS
- Sentence length SD: ~10 words -- PASS
- Formulaic transitions: 0 -- PASS
- No promotional tone -- PASS
- Bold: 0 decorative instances -- PASS
- Specificity: concrete code examples -- PASS
- Voice: professional-casual, peer-to-peer -- PASS
