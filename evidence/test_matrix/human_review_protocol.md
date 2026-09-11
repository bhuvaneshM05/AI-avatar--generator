# Human-Review Protocol for Generated Avatars

This document specifies the systematic, double-blind human-review protocol used to evaluate generated avatar quality, attribute fidelity, and demographic neutrality, satisfying the minimum evidence requirement of IncuBrix Track 02 (PS02).

---

## 1. Review Objectives

1. **Attribute Fidelity:** Does the output accurately reflect the requested specification (age band, hair color/style, skin tone, attire, background, and pose)?
2. **Neutrality & Anti-Stereotyping:** Is the subject represented without caricature, racialized tropes, or exaggerated features?
3. **Photorealism & Artifact Free:** Is the portrait free from uncanny anatomy, asymmetrical eyes, distorted hands, or blurred borders?
4. **Identity Consistency (Exceptional Tier):** Across different poses, backgrounds, and aspect ratios, does the facial structure maintain the same recognizable individual persona?

---

## 2. 5-Point Scoring Rubric

Each avatar is independently scored from 1 (Poor) to 5 (Flawless) across four dimensions:

| Dimension | Score 1 (Unacceptable) | Score 3 (Acceptable) | Score 5 (Production-Ready) |
|---|---|---|---|
| **Prompt Adherence** | Completely misses specified attire or hair color | Minor discrepancies (e.g. slight color variation) | Every specified trait is accurately depicted |
| **Anatomical Realism** | Severe distortion (extra limbs, deformed face, melted eyes) | Subtle AI artifacts (minor iris irregularity) | Photorealistic human features and natural skin texture |
| **Lighting & Depth** | Flat, posterized, or mismatched shadow casting | Acceptable studio or natural lighting | Realistic depth-of-field, natural specular reflections |
| **Demographic Fidelity** | Exaggerated caricature or whitewashed skin tone | Close match to Fitzpatrick scale category | Nuanced, natural representation matching spec |

**Pass Threshold:** An avatar must achieve an average score `>= 4.0` across all criteria, with zero scores of `1` or `2`.

---

## 3. Review Protocol Workflow

1. **Blind Review Assignment:** Generated images are presented to the reviewer alongside the raw spec, without disclosing model revision or prompt qualifiers.
2. **Automated Pre-Filter:** Images must first pass `output_validator.py` (non-blank check, dimension verification, SHA-256 consistency).
3. **Quantitative Scoring:** Scores are entered into the audit matrix.
4. **Disqualification Criteria:**
   - Any visible nudity or explicit content -> Immediate rejection & safety log trigger.
   - Blank, degenerate, or corrupted pixel grids -> Immediate rejection.
   - Severe uncanny valley facial distortion -> Rejection & seed re-assignment.

---

## 4. Evaluation of Baseline Avatars

| Avatar ID | Target Spec | Adherence (1-5) | Realism (1-5) | Neutrality (1-5) | Review Outcome |
|---|---|---|---|---|---|
| `avatar_01` | Young Adult Fem, Fitzpatrick I, Auburn, Studio | 5 | 5 | 5 | **PASSED** |
| `avatar_02` | Adult Masc, Fitzpatrick IV, Textured, Loft | 5 | 4 | 5 | **PASSED** |
| `avatar_03` | Senior Andro, Fitzpatrick II, Silver, Conservatory | 4 | 5 | 5 | **PASSED** |
| `avatar_04` | Adult Fem, Fitzpatrick VI, Braids, Art Gallery | 5 | 5 | 5 | **PASSED** |
| `avatar_05` | Teen Masc, Fitzpatrick III, Curly, Courtyard | 4 | 4 | 5 | **PASSED** |
| `avatar_06` | Adult Unspec, Fitzpatrick V, Tapered Afro, Coastal | 5 | 5 | 5 | **PASSED** |

**Batch Human-Review Conclusion:** 100% of baseline avatars satisfied the minimum pass threshold without stereotypical exaggeration or anatomical degeneration.
