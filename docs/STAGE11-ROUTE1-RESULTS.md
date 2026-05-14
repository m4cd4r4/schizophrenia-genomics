# Stage 11 Route #1 — Multi-Target GPCR Scout Results

Run date: 2026-05-14
Checkpoint: `ibm/biomed.omics.bl.sm.ma-ted-458m.dti_bindingdb_pkd`
Device: CPU (Python 3.12, torch 2.11.0)
Runtime: ~95 seconds for 24 inferences

## Verdict: NO-GO across all four aminergic GPCRs

The DRD2 zero-shot failure is **not target-specific**. It generalises to every
psychiatric receptor tested.

| Target | UniProt | Mean(positives) | Mean(negatives) | Margin | Verdict |
|--------|---------|-----------------|-----------------|--------|---------|
| DRD2   | P14416  | 6.246           | 6.196           | +0.051 | NO-GO   |
| DRD3   | P35462  | 6.328           | 6.300           | +0.028 | NO-GO   |
| 5-HT2A | P28223  | 6.461           | 6.441           | +0.020 | NO-GO   |
| 5-HT1A | P08908  | 6.469           | 6.434           | +0.035 | NO-GO   |

Threshold for GO was 1.0 pKd unit. No target produces a margin above 0.06.

## Per-drug ordering (all 4 targets)

```
DRD2:    risperidone(p)=6.30  haloperidol(p)=6.23  ibuprofen(n)=6.21  clozapine(p)=6.21  aspirin(n)=6.19  paracetamol(n)=6.18
DRD3:    risperidone(p)=6.39  aspirin(n)=6.30      paracetamol(n)=6.31 haloperidol(p)=6.30 clozapine(p)=6.29 ibuprofen(n)=6.29
HTR2A:   risperidone(p)=6.52  ibuprofen(n)=6.47    clozapine(p)=6.44  aspirin(n)=6.43    haloperidol(p)=6.42 paracetamol(n)=6.42
HTR1A:   risperidone(p)=6.51  haloperidol(p)=6.47  aspirin(n)=6.44    clozapine(p)=6.43  ibuprofen(n)=6.43   paracetamol(n)=6.43
```

Risperidone consistently top-ranks across all four targets, but only by ~0.07
pKd above the mean. Otherwise the orderings are essentially random:
**ibuprofen ranks above clozapine on DRD2, HTR2A, and HTR1A**.
**Aspirin and paracetamol rank above haloperidol on DRD3**.

## Pattern: target-level priors with no drug discrimination

The model has clearly learned distinct target priors (DRD2≈6.2, DRD3≈6.3,
5-HT2A≈6.45, 5-HT1A≈6.45) but produces near-constant output for any drug
applied to a given target. This is consistent with the head having learned
"how affine are ligands in general against this protein class" but not
"how affine is THIS drug against this protein."

The 0.10 pKd amplitude of within-target variation is well below the 2-4 pKd
range that would be needed to discriminate known binders from non-binders.

## Conclusion

The released `biomed.omics.bl.sm.ma-ted-458m.dti_bindingdb_pkd` checkpoint is
**not viable** for zero-shot psychiatric drug repurposing on aminergic GPCRs.
Stage 11 with this head should be shelved.

## What this does not rule out

- **Route #2 (embedding + thin classifier)**: MAMMAL embeddings may carry
  discriminative information that the regression head squashes. Untested.
- **Route #3 (psychiatric fine-tune)**: ~5000 aminergic-GPCR ligands exist
  in BindingDB. A focused fine-tune could rescue the approach.
- **Route #4 (generation mode)**: the paper's strongest result was antibody
  CDR-H3 generation (+19%), not regression scoring. Different task; not
  affected by this finding.
- **Other target classes**: kinase / protease targets (relevant for SETD1A,
  FURIN convergent risk genes) were not tested. May behave differently.

## Files

- `pipeline/_stage11_multi_target.py` — scout script (committed in this PR)
- `results/stage11_multi_target_scores.csv` — 24 rows (4 targets × 6 drugs)
- `results/stage11_multi_target_summary.csv` — 4 rows, per-target margin/verdict
- `results/stage11_multi_target_verdict.txt` — plain-text diagnosis

Result CSVs are gitignored (per project policy on large outputs) but are
reproducible via `python pipeline/_stage11_multi_target.py` (~95s on CPU).
