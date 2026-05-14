"""Stage 11 scout, route #1: same drug panel, multiple psychiatric targets.

Tests whether the DRD2 zero-shot failure is target-specific or general to
aminergic GPCRs. If 5-HT2A / 5-HT1A / DRD3 produce clean discrimination but
DRD2 does not, BindingDB under-representation of DRD2 is the diagnosis and
a targeted fine-tune could rescue the approach.

Same panel: 3 antipsychotics (haloperidol, clozapine, risperidone) and 3
non-psychiatric controls (aspirin, paracetamol, ibuprofen). All three
antipsychotics bind 5-HT2A and DRD3; risperidone and clozapine bind 5-HT1A.
None of the negatives have appreciable affinity for any.
"""
import os
os.environ.setdefault("HF_HOME", "I:/hf-cache")
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", "I:/hf-cache/hub")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
import pandas as pd
import config
from pipeline.utils import get_logger, save_df
from pipeline.stage11_mammal_scout import load_mammal, score_dti, DRUG_PANEL

log = get_logger("stage11_multi")

TARGETS = {
    "DRD2":   ("P14416", "Dopamine D2 receptor"),
    "DRD3":   ("P35462", "Dopamine D3 receptor"),
    "HTR2A":  ("P28223", "Serotonin 5-HT2A receptor"),
    "HTR1A":  ("P08908", "Serotonin 5-HT1A receptor"),
}

GO_MARGIN = 1.0


def fetch_uniprot_seq(uniprot_id: str) -> str:
    cache = config.DATA_PROCESSED / f"{uniprot_id}.fasta"
    if cache.exists():
        text = cache.read_text()
    else:
        url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
        log.info(f"Fetching {uniprot_id} from UniProt")
        r = requests.get(url, timeout=30); r.raise_for_status()
        text = r.text
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text)
    lines = [ln.strip() for ln in text.splitlines() if ln and not ln.startswith(">")]
    return "".join(lines)


def main():
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    sequences = {sym: (uid, fetch_uniprot_seq(uid), desc)
                 for sym, (uid, desc) in TARGETS.items()}
    for sym, (uid, seq, desc) in sequences.items():
        log.info(f"  {sym:6s} ({uid}) {len(seq):4d} aa  {desc}")

    model, tokenizer_op, device = load_mammal()

    rows = []
    for sym, (uid, seq, desc) in sequences.items():
        log.info(f"\n=== {sym} ({uid}) ===")
        for drug, (label, smiles) in DRUG_PANEL.items():
            log.info(f"Scoring {drug:12s} ({label}) against {sym}...")
            try:
                score = score_dti(model, tokenizer_op, device, seq, smiles)
            except Exception as e:
                log.error(f"  failed: {e}")
                score = float("nan")
            rows.append({
                "target": sym, "uniprot": uid, "target_desc": desc,
                "drug": drug, "label": label, "smiles": smiles,
                "affinity_score": score,
            })
            log.info(f"  pKd = {score:.4f}")

    df = pd.DataFrame(rows)
    save_df(df, config.RESULTS_DIR / "stage11_multi_target_scores.csv",
            "stage11 multi-target affinity scores")

    # Per-target verdict
    lines = ["Stage 11 multi-target scout — route #1", "=" * 60, ""]
    summary_rows = []
    for sym in TARGETS:
        sub = df[df.target == sym]
        pos = sub[sub.label == "positive"]["affinity_score"].dropna()
        neg = sub[sub.label == "negative"]["affinity_score"].dropna()
        margin = pos.mean() - neg.mean() if len(pos) and len(neg) else float("nan")
        verdict = "GO" if margin >= GO_MARGIN else "NO-GO"
        summary_rows.append({"target": sym, "uniprot": TARGETS[sym][0],
                             "mean_pos": pos.mean(), "mean_neg": neg.mean(),
                             "margin": margin, "verdict": verdict})
        lines.append(f"{sym:6s}  pos={pos.mean():.3f}  neg={neg.mean():.3f}  "
                     f"margin={margin:+.3f}  -> {verdict}")
        lines.append(f"        per-drug: " + ", ".join(
            f"{r.drug}={r.affinity_score:.2f}({r.label[0]})"
            for r in sub.itertuples()))
        lines.append("")

    summary = pd.DataFrame(summary_rows)
    save_df(summary, config.RESULTS_DIR / "stage11_multi_target_summary.csv",
            "stage11 multi-target verdict summary")

    # Overall diagnosis
    n_go = sum(1 for r in summary_rows if r["verdict"] == "GO")
    if n_go == 0:
        lines.append("DIAGNOSIS: failure is GENERAL across aminergic GPCRs.")
        lines.append("The released DTI head does not discriminate psychiatric")
        lines.append("drugs on any tested target. Route #1 result: shelve")
        lines.append("Stage 11 with DTI head. Consider routes #2 (embedding)")
        lines.append("or #4 (generation) if still motivated.")
    elif n_go == len(TARGETS):
        lines.append("DIAGNOSIS: all targets pass — earlier DRD2 result may have")
        lines.append("been transient. Re-verify before declaring GO.")
    else:
        passing = [r["target"] for r in summary_rows if r["verdict"] == "GO"]
        failing = [r["target"] for r in summary_rows if r["verdict"] != "GO"]
        lines.append(f"DIAGNOSIS: target-class heterogeneity.")
        lines.append(f"  Passing: {', '.join(passing)}")
        lines.append(f"  Failing: {', '.join(failing)}")
        lines.append("Stage 11 viable for the passing-target subset. Investigate")
        lines.append("whether the failing targets are under-represented in")
        lines.append("BindingDB. Targeted fine-tune may rescue full coverage.")

    verdict_path = config.RESULTS_DIR / "stage11_multi_target_verdict.txt"
    verdict_path.write_text("\n".join(lines))
    log.info(f"Wrote verdict: {verdict_path}")
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
