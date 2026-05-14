# Stage 11 — MAMMAL Cross-Modal Drug Repurposing

## What this is

A scout experiment + planned full stage that tests whether IBM's MAMMAL
biomedical foundation model can improve on Stage 9's classical CMap/LINCS-NES
drug repurposing.

**Paper:** [MAMMAL — npj Drug Discovery (Shoshan et al., 2026)](https://www.nature.com/articles/s44386-026-00047-4)
**Weights:** [ibm/biomed.omics.bl.sm.ma-ted-458m](https://huggingface.co/ibm/biomed.omics.bl.sm.ma-ted-458m)
**Code:** [BiomedSciAI/biomed-multi-alignment](https://github.com/BiomedSciAI/biomed-multi-alignment)

## Scout (day 1, ~30 min of GPU time)

Goal: prove the method transfers before committing two weeks to a full build.

Method: score 3 antipsychotics (haloperidol, clozapine, risperidone) and 3
non-psychiatric controls (aspirin, paracetamol, ibuprofen) for binding affinity
against DRD2 (the dopamine D2 receptor, canonical antipsychotic target).

Verdict logic:
- mean(positives) - mean(negatives) >= 1.0 (log-affinity units) → **GO**, build full Stage 11
- otherwise → **NO-GO**, method does not transfer cleanly

### Install

```bash
pip install -r requirements-mammal.txt
```

GPU strongly recommended. On CPU expect ~10 min/score (1 hour for the panel).
On a consumer RTX card expect ~5 sec/score.

### Run

```bash
python -m pipeline.stage11_mammal_scout
```

The model (~2GB) downloads to `I:/hf-cache/hub/` (existing HF cache, ~39GB
of other models there) on first run.

### Outputs

- `results/stage11_scout_scores.csv` — one row per (drug, target) pair
- `results/stage11_scout_verdict.txt` — plain-text GO / NO-GO decision

## Full Stage 11 (only if scout returns GO)

Three substages — see `pipeline/` (not yet implemented):

| Substage | Purpose | Approx effort |
|----------|---------|---------------|
| 11a | Build query set from Stage 2 meta-significant genes + Stage 4 convergent risk genes | 2 days |
| 11b | Score drug library (~10k compounds) × queries via MAMMAL DTI + transcriptomic heads | 3-5 days |
| 11c | Disagreement analysis vs Stage 9 NES rankings, mechanistic triage of top 20 disagreements | 3 days |

Plus ~2 days for dashboard integration (DuckDB table + Next.js tab).

## Risks (must address before publication)

1. **Brain transcriptome coverage** — MAMMAL trained on Cell×Gene; brain
   coverage is present (Allen Brain Atlas) but less dense than blood/cancer.
   Mitigation: start with GSE38484 + GSE27383 (blood) where MAMMAL's training
   distribution is densest.

2. **Zero-shot vs fine-tuning** — paper results use task-specific fine-tuning.
   Scout uses zero-shot DTI. If scout is borderline GO (margin 0.5-1.0), try
   one fine-tuning round on BindingDB psychiatric-drug subset before scaling.

3. **Reproducibility** — Stages 1-10 are CPU-only and fully reproducible from
   public GEO. Stage 11 needs GPU. Mitigation: checkpoint MAMMAL outputs to
   CSV after inference and treat CSV as input to downstream stages (same
   pattern as Stage 1 GEO cache).

## Publication angle (if full Stage 11 succeeds)

Target venues: *Bioinformatics*, *Briefings in Bioinformatics*, *npj Mental Health Research*.

Framing: "First application of MAMMAL to psychiatric drug repurposing.
Head-to-head with classical GSEA-CMap on schizophrenia transcriptomic data.
We find X disagreements between the two methods, of which Y are mechanistically
defensible (binding a PGC3 risk gene), suggesting MAMMAL captures
target-level information that signature-similarity methods miss."

Not Nature-tier unless wet-lab validation is added on a top disagreement.
