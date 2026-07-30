# Source Ledger

Every source the discovery pass has vetted, with the verdict and when it was last checked. **This file is the learner's own accreted floor** — the `primer/source-canon.md` in the public core is a shared *starter pack*, and it is never written to by a lesson (it's a shared repo you pull updates into; a personal promotion there would both leak what you study and conflict on every pull). Contributing a source upstream is a deliberate PR, not a side effect of a lesson.

**Bookkeeping is owned by `tools/primer_sources.py`, not the model** — it parses and rewrites these lines deterministically, so freshness is arithmetic rather than something the model eyeballs. Hand-editing is fine; keep the field format.

What this buys, and why the file exists: a source vetted in one lesson is **reused** in the next instead of being re-swept and re-judged. The mandatory per-lesson discovery pass (`primer/research-protocol.md`) therefore gets cheaper the more it runs, which is what makes "currency is non-negotiable" sustainable rather than something that quietly degrades under time pressure.

Source line format (under `## Sources`):

`- url:<url> | domain:<d> | tag:<verified|from-training> | verdict:<cite|caveat|dropped> | seen:<YYYY-MM-DD> | checked:<YYYY-MM-DD> | floor:<yes|no> | used:<n> | why:<one line>`

- `tag` — `verified` means fetched and read in a session; `from-training` means asserted from model training and **not yet grounded**. The `from-training` entries are the verify backlog (`sources-unverified`).
- `verdict` — `cite` (load-bearing, use it), `caveat` (usable with a stated limitation), `dropped` (failed the stale-criteria; recorded so it isn't re-judged).
- `checked` — last time the entry was actually re-validated. Freshness is measured from here (`sources-stale`), not from `seen`.
- `floor` — `yes` marks a source that proved load-bearing and should be part of the domain's starting set for future lessons (`sources-floor`). This is what "promotion" means now.
- `used` — how many lessons leaned on it. A high count with a stale `checked` is the first thing to re-verify.

---

## Sources

<sources appended here>

---

## Domain sweeps

When each domain last had a full discovery sweep. Within the freshness horizon a lesson reads the ledger and does a *narrow* top-up for its specific topic; past it, the full sweep re-runs. The horizon is the currency guardrail — the top-up is still mandatory (`primer/source-canon.md`).

Format: `- domain:<d> | swept:<YYYY-MM-DD> | note:<one line>`

---
