"""Canonical-input sanity check: replicate the main_infer.py defaults using
our inlined inference path. If MAMMAL produces a pKd far from the prior mean
(5.79) on the canonical inputs, the inference path is correct and the
DRD2 NO-GO is real. If it also collapses to ~5.79, the setup is broken.
"""
import os
os.environ.setdefault("HF_HOME", "I:/hf-cache")
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", "I:/hf-cache/hub")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.stage11_mammal_scout import load_mammal, score_dti

# Defaults from mammal/examples/dti_bindingdb_kd/main_infer.py
CANONICAL_TARGET = "NLMKRCTRGFRKLGKCTTLEEEKCKTLYPRGQCTCSDSKMNTHSCDCKSC"
CANONICAL_DRUG = "CC(=O)NCCC1=CNc2c1cc(OC)cc2"  # melatonin

print("Sanity-check: running MAMMAL DTI on canonical example (kappa-bungarotoxin + melatonin)")
print(f"Target: {CANONICAL_TARGET[:30]}...({len(CANONICAL_TARGET)} aa)")
print(f"Drug:   {CANONICAL_DRUG} (melatonin)")
print()

model, tokenizer_op, device = load_mammal()
score = score_dti(model, tokenizer_op, device, CANONICAL_TARGET, CANONICAL_DRUG)
print(f"\nCanonical pKd prediction = {score:.4f}")
print(f"Training mean = 5.79, training std = 1.34")
print(f"Distance from prior mean: {abs(score - 5.79):.3f}")
print()
if abs(score - 5.79) < 0.2:
    print("WARNING: canonical output near prior mean — inference path may be broken")
else:
    print("OK: canonical output meaningfully different from prior — inference is wiring correctly")
