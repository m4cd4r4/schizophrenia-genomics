"""
Stage 11 (scout): Go / no-go test for MAMMAL cross-modal scoring.

PURPOSE
    Decide in ~30 min of GPU time whether MAMMAL transfers from its training
    distribution (cancer + general bio) to psychiatric drug repurposing well
    enough to justify a full Stage 11 build (~2 weeks).

METHOD
    Use MAMMAL's drug-target binding affinity (DTI) head to score canonical
    antipsychotics vs non-psychiatric controls against the dopamine D2 receptor
    (DRD2, UniProt P14416) — the canonical target every approved antipsychotic
    binds.

    Positive controls (must score high):   haloperidol, clozapine, risperidone
    Negative controls (must score low):    aspirin, paracetamol, ibuprofen

VERDICT
    GO    : mean(positives) - mean(negatives) >= GO_MARGIN  → build full Stage 11
    NO-GO : otherwise                                       → method doesn't transfer

USAGE
    python -m pipeline.stage11_mammal_scout
    (uses HF cache at I:/hf-cache/ — already 39GB of models there)

OUTPUT
    results/stage11_scout_scores.csv      one row per (drug, target) with score
    results/stage11_scout_verdict.txt     plain-text GO / NO-GO with margin
"""
import os
import sys
from pathlib import Path

# Redirect Hugging Face cache to existing I:/hf-cache BEFORE importing HF libs.
# This is where I:/hf-cache/hub already holds 39GB of models (Flux, SDXL, etc.).
os.environ.setdefault("HF_HOME", "I:/hf-cache")
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", "I:/hf-cache/hub")

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from pipeline.utils import get_logger, save_df

log = get_logger("stage11_scout")

# --- Reference target: dopamine D2 receptor (DRD2) ---
# Canonical antipsychotic target. Every FDA-approved antipsychotic binds it.
DRD2_UNIPROT = "P14416"
UNIPROT_FASTA_URL = f"https://rest.uniprot.org/uniprotkb/{DRD2_UNIPROT}.fasta"
DRD2_CACHE = config.DATA_PROCESSED / "DRD2_P14416.fasta"

# --- Drug panel: 3 positives + 3 negatives ---
DRUG_PANEL = {
    # Positive controls — known DRD2 binders, all FDA-approved antipsychotics
    "haloperidol":  ("positive", "OC(c1ccc(F)cc1)(CCCN2CCC(CC2)(c3ccc(Cl)cc3)O)"),
    "clozapine":    ("positive", "CN1CCN(CC1)C2=Nc3cc(Cl)ccc3Nc4ccccc24"),
    "risperidone":  ("positive", "CC1=C(C(=O)N2CCCCC2=N1)CCN3CCC(CC3)c4noc5cc(F)ccc45"),
    # Negative controls — no expected DRD2 affinity
    "aspirin":      ("negative", "CC(=O)Oc1ccccc1C(=O)O"),
    "paracetamol":  ("negative", "CC(=O)Nc1ccc(O)cc1"),
    "ibuprofen":    ("negative", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"),
}

GO_MARGIN = 1.0  # log10(Kd) units — positives must beat negatives by this much


def fetch_drd2_sequence() -> str:
    """Fetch DRD2 protein sequence from UniProt, cache to disk."""
    if DRD2_CACHE.exists():
        text = DRD2_CACHE.read_text()
    else:
        log.info(f"Fetching DRD2 sequence from {UNIPROT_FASTA_URL}")
        resp = requests.get(UNIPROT_FASTA_URL, timeout=30)
        resp.raise_for_status()
        text = resp.text
        DRD2_CACHE.parent.mkdir(parents=True, exist_ok=True)
        DRD2_CACHE.write_text(text)
        log.info(f"Cached DRD2 FASTA to {DRD2_CACHE}")
    # Strip FASTA header, concatenate sequence lines
    lines = [ln.strip() for ln in text.splitlines() if ln and not ln.startswith(">")]
    seq = "".join(lines)
    log.info(f"DRD2 sequence loaded: {len(seq)} aa")
    return seq


# DTI-finetuned MAMMAL checkpoint — has the proper pKd regression head.
# Base ma-ted-458m is multi-task pretrained; this is the BindingDB-pKd finetune.
MAMMAL_DTI_CKPT = "ibm/biomed.omics.bl.sm.ma-ted-458m.dti_bindingdb_pkd"

# Default normalisation constants from the checkpoint's training (BindingDB pKd):
NORM_Y_MEAN = 5.79384684128215
NORM_Y_STD = 1.33808027428196


def _dti_data_preprocessing(
    sample_dict, *, tokenizer_op,
    target_max_seq_length=1250, drug_max_seq_length=256,
    encoder_input_max_seq_len=1512, device="cpu",
):
    """Inlined from mammal.examples.dti_bindingdb_kd.task.DtiBindingdbKdTask.

    We avoid `from mammal.examples.dti_bindingdb_kd.task import DtiBindingdbKdTask`
    because that chain pulls in pytdc -> tiledbsoma, which does not build on
    Windows (training-only data loader).
    """
    import torch
    from mammal.keys import (
        ENCODER_INPUTS_STR, ENCODER_INPUTS_TOKENS,
        ENCODER_INPUTS_ATTENTION_MASK, ENCODER_INPUTS_SCALARS,
    )
    target_seq = sample_dict["target_seq"]
    drug_seq = sample_dict["drug_seq"]
    sample_dict[ENCODER_INPUTS_STR] = (
        "<@TOKENIZER-TYPE=AA><MASK>"
        f"<@TOKENIZER-TYPE=AA@MAX-LEN={target_max_seq_length}>"
        f"<MOLECULAR_ENTITY><MOLECULAR_ENTITY_GENERAL_PROTEIN>"
        f"<SEQUENCE_NATURAL_START>{target_seq}<SEQUENCE_NATURAL_END>"
        f"<@TOKENIZER-TYPE=SMILES@MAX-LEN={drug_max_seq_length}>"
        f"<MOLECULAR_ENTITY><MOLECULAR_ENTITY_SMALL_MOLECULE>"
        f"<SEQUENCE_NATURAL_START>{drug_seq}<SEQUENCE_NATURAL_END>"
        "<EOS>"
    )
    tokenizer_op(
        sample_dict,
        key_in=ENCODER_INPUTS_STR,
        key_out_tokens_ids=ENCODER_INPUTS_TOKENS,
        key_out_attention_mask=ENCODER_INPUTS_ATTENTION_MASK,
        max_seq_len=encoder_input_max_seq_len,
        key_out_scalars=ENCODER_INPUTS_SCALARS,
    )
    sample_dict[ENCODER_INPUTS_TOKENS] = torch.tensor(
        sample_dict[ENCODER_INPUTS_TOKENS], device=device,
    )
    sample_dict[ENCODER_INPUTS_ATTENTION_MASK] = torch.tensor(
        sample_dict[ENCODER_INPUTS_ATTENTION_MASK], device=device,
    )
    return sample_dict


def _dti_process_output(batch_dict, *, norm_y_mean, norm_y_std):
    """Inlined post-processing: de-normalise pKd regression output."""
    from mammal.keys import SCALARS_PREDICTION_HEAD_LOGITS
    scalars_preds = batch_dict[SCALARS_PREDICTION_HEAD_LOGITS]
    batch_dict["model.out.dti_bindingdb_kd"] = (
        scalars_preds[:, 0] * norm_y_std + norm_y_mean
    )
    return batch_dict


def load_mammal():
    """Load DTI-finetuned MAMMAL model + tokenizer."""
    log.info(f"Loading MAMMAL DTI checkpoint ({MAMMAL_DTI_CKPT})...")
    import torch
    from fuse.data.tokenizers.modular_tokenizer.op import ModularTokenizerOp
    from mammal.model import Mammal

    model = Mammal.from_pretrained(MAMMAL_DTI_CKPT)
    model.eval()
    if torch.cuda.is_available():
        device = "cuda"
        log.info(f"MAMMAL on GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        log.warning("No CUDA — running on CPU. Will be slow but functional.")
    model = model.to(device)
    tokenizer_op = ModularTokenizerOp.from_pretrained(MAMMAL_DTI_CKPT)
    return model, tokenizer_op, device


def score_dti(model, tokenizer_op, device, protein_seq: str, smiles: str) -> float:
    """Score one (drug, target) pair. Returns pKd = -log10(Kd) in mol/L."""
    sample = {"target_seq": protein_seq, "drug_seq": smiles}
    sample = _dti_data_preprocessing(sample, tokenizer_op=tokenizer_op, device=device)
    batch = model.forward_encoder_only([sample])
    batch = _dti_process_output(batch, norm_y_mean=NORM_Y_MEAN, norm_y_std=NORM_Y_STD)
    return float(batch["model.out.dti_bindingdb_kd"][0])


def run():
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    drd2_seq = fetch_drd2_sequence()
    model, tokenizer_op, device = load_mammal()

    rows = []
    for drug, (label, smiles) in DRUG_PANEL.items():
        log.info(f"Scoring {drug:12s} ({label}) against DRD2...")
        try:
            score = score_dti(model, tokenizer_op, device, drd2_seq, smiles)
        except Exception as e:
            log.error(f"  failed: {e}")
            score = float("nan")
        rows.append({
            "drug": drug,
            "label": label,
            "target": "DRD2",
            "uniprot": DRD2_UNIPROT,
            "smiles": smiles,
            "affinity_score": score,
        })
        log.info(f"  score = {score}")

    df = pd.DataFrame(rows).sort_values("affinity_score", ascending=False)
    save_df(df, config.RESULTS_DIR / "stage11_scout_scores.csv",
            "stage11 scout affinity scores")

    # --- Verdict ---
    pos = df[df.label == "positive"]["affinity_score"].dropna()
    neg = df[df.label == "negative"]["affinity_score"].dropna()

    verdict_path = config.RESULTS_DIR / "stage11_scout_verdict.txt"
    if len(pos) < 2 or len(neg) < 2:
        verdict = "INCONCLUSIVE: too many failed scorings"
        margin = None
    else:
        margin = pos.mean() - neg.mean()
        if margin >= GO_MARGIN:
            verdict = (
                f"GO: positives beat negatives by {margin:.2f} "
                f"(threshold {GO_MARGIN}). MAMMAL transfers to DRD2 binding "
                f"— proceed with full Stage 11 build."
            )
        else:
            verdict = (
                f"NO-GO: positives beat negatives by only {margin:.2f} "
                f"(threshold {GO_MARGIN}). MAMMAL does not cleanly recover "
                f"the canonical antipsychotic-DRD2 relationship. Do NOT invest "
                f"two weeks in full Stage 11. Consider fine-tuning on "
                f"psychiatric-drug data first, or revisit feasibility."
            )

    body = [
        "Stage 11 scout — MAMMAL drug-target binding sanity check",
        "=" * 60,
        f"Target:      DRD2 ({DRD2_UNIPROT}), {len(drd2_seq)} aa",
        f"Positives:   {', '.join(df[df.label=='positive']['drug'])}",
        f"Negatives:   {', '.join(df[df.label=='negative']['drug'])}",
        "",
        f"Mean(positive) = {pos.mean():.3f}" if len(pos) else "Mean(positive) = NaN",
        f"Mean(negative) = {neg.mean():.3f}" if len(neg) else "Mean(negative) = NaN",
        f"Margin         = {margin:.3f}" if margin is not None else "Margin         = N/A",
        f"Threshold      = {GO_MARGIN}",
        "",
        "Per-drug scores:",
        df.to_string(index=False),
        "",
        "VERDICT:",
        verdict,
    ]
    verdict_path.write_text("\n".join(body))
    log.info(f"Wrote verdict: {verdict_path}")
    print("\n" + "\n".join(body))


if __name__ == "__main__":
    run()
