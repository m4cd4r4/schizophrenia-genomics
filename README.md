# Schizophrenia Transcriptomics Pipeline

> **Work in progress** - findings are preliminary and not peer-reviewed. Pipeline and datasets are actively being extended.

A computational pipeline for analysing publicly available gene expression data in schizophrenia. Combines differential expression, co-expression network analysis, GWAS risk loci mapping, pathway enrichment, cell type deconvolution, PPI network construction, drug repurposing, and medication dose-response analysis across **five datasets** spanning whole blood, PBMC, prefrontal cortex, hippocampus, and striatum.

**Live dashboard:** [schizophrenia-genomics.vercel.app](https://schizophrenia-genomics.vercel.app)

---

## Background

Inspired by the Galvin family case documented in *Hidden Valley Road* (Robert Galvin, 2020) and the decades of research by Lynn DeLisi and Robert Freedman, this project asks: what do publicly available transcriptomic datasets reveal about the molecular basis of schizophrenia, and can we computationally identify drug repurposing candidates that reverse the disease signature?

The analysis is entirely reproducible from public GEO data with no access-controlled resources required.

---

## Datasets

| ID | Tissue | Platform | SCZ | Control | Total | Description |
|----|--------|----------|-----|---------|-------|-------------|
| **GSE38484** | Whole blood | Illumina HT-12 V3 (GPL6947) | 106 | 96 | 202 | Primary dataset - co-expression network |
| **GSE27383** | PBMC | Affymetrix HG-U133 Plus 2.0 (GPL570) | 43 | 29 | 72 | Acutely psychotic patients |
| **GSE21138** | Prefrontal cortex BA46 | Affymetrix HG-U133 Plus 2.0 (GPL570) | 30 | 29 | 59 | Post-mortem; detailed medication records |
| **GSE53987** | PFC + hippocampus + striatum | Affymetrix HG-U133 Plus 2.0 (GPL570) | 48 | 55 | 103 | Three brain regions; also BD and MDD |
| **GSE12649** | Prefrontal cortex BA46 | Affymetrix HG-U133A (GPL96) | 35 | 34 | 69 | Mitochondrial dysfunction focus |

GSE21138 contains chlorpromazine-equivalent dosing data for 27 SCZ patients across 10 antipsychotic drug types, enabling medication dose-response and blood-brain confounding analysis.

GSE92538 was evaluated and excluded: custom Affymetrix Gene 1.0 ST platform (GPL10526/GPL17027) maps only 59 of 11,973 probes to standard gene symbols.

---

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              GEO Public Data                                     │
│  GSE38484 (blood)  GSE27383 (PBMC)  GSE21138 (PFC)  GSE53987 (3 regions)       │
│                                                       GSE12649 (PFC mito)        │
└──────────────────────────────────┬───────────────────────────────────────────────┘
                                   │
                            ┌──────▼──────┐
                            │  Stage 1    │
                            │  Download   │
                            │  GEOparse   │
                            │  probe map  │
                            └──────┬──────┘
                                   │
               ┌───────────────────┼───────────────────┐
               │                   │                   │
        ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
        │  Stage 2    │     │  Stage 3    │     │  Stage 7    │
        │  Diff Expr  │     │  WGCNA      │     │  Cell type  │
        │  t-test+FDR │     │  co-expr    │     │  deconv     │
        │  meta-anal  │     │  networks   │     │  MCPcounter │
        └──────┬──────┘     └──────┬──────┘     └─────────────┘
               │                   │
        ┌──────▼──────┐     ┌──────▼──────┐
        │  Stage 4    │     │  Stage 6    │
        │  Risk loci  │     │  Module     │
        │  PGC3+fam   │     │  preserv.  │
        │  overlap    │     │  Zsummary  │
        └──────┬──────┘     └─────────────┘
               │
        ┌──────▼──────┐     ┌─────────────┐     ┌─────────────┐
        │  Stage 5    │     │  Stage 8    │     │  Stage 9    │
        │  Pathways   │     │  PPI nets   │     │  Drug       │
        │  GSEA+Enr   │     │  STRING DB  │     │  repurpos.  │
        │  dashboard  │     │  community  │     │  CMap/LINCS │
        └─────────────┘     └─────────────┘     └──────┬──────┘
                                                        │
                                                 ┌──────▼──────┐
                                                 │  Stage 10   │
                                                 │  Medication │
                                                 │  dose-resp  │
                                                 │  blood-brain│
                                                 └─────────────┘
```

Each stage reads inputs from disk and writes outputs independently, allowing any stage to be re-run in isolation:

```bash
python run.py --stages 2,3    # Re-run only DE and co-expression
python run.py --stages 9,10   # Drug repurposing only
python run.py --stages 3,5,7,8,9,10 --datasets GSE53987,GSE12649  # New datasets only
```

---

## Results Summary

### Stage 2 - Differential Expression

Welch's t-test with Benjamini-Hochberg FDR correction. Microarray data is log2-normalised at source; no additional normalisation applied.

| Dataset | Tissue | Genes tested | FDR < 0.05 | \|logFC\| > 0.5 |
|---------|--------|-------------|------------|-----------------|
| GSE38484 | Whole blood | 25,142 | 4,777 | 33 |
| GSE27383 | PBMC | 23,520 | 825 | 16 |
| GSE21138 | PFC (post-mortem) | 15,706 | 0 | 0 |
| GSE53987 | PFC/hippo/striatum | 23,520 | 5 | 5 |
| GSE12649 | PFC (mito focus) | 13,515 | 0 | 0 |

> GSE21138 and GSE12649 show no FDR-significant genes individually. This is expected at n=59 and n=69 respectively: post-mortem brain has high technical variance (PMI, pH, freezing artifacts) that inflates within-group variance and reduces power. GSE53987 reaches only 5 genes despite n=103, likely reflecting the multi-region heterogeneity.

**Meta-analysis** (Fisher's method across all 5 datasets, 7,797 common genes):
- 2,028 meta-significant genes (combined FDR < 0.05)
- 214 direction-consistent across all datasets

Top meta-analysis genes (ranked by combined FDR):

```
Rank  Gene       mean logFC   direction consistent
 1    NRGN         +0.41            Yes
 2    TCF4         +0.28            Yes
 3    FOXP1        +0.22            Yes
 4    SETD1A       +0.19            Yes
 5    INO80        +0.31            Yes
```

---

### Stage 3 - Co-expression Networks (WGCNA-style)

Computed on the top 5,000 most variable genes (median absolute deviation). Soft-thresholding power selected to achieve scale-free topology R² > 0.85. Modules detected via hierarchical clustering on TOM dissimilarity matrix.

| Dataset | Tissue | Soft power | Modules | SCZ-correlated (r > 0.3) |
|---------|--------|-----------|---------|--------------------------|
| GSE38484 | Whole blood | 6 | 10 | M1, M3, M6 |
| GSE27383 | PBMC | 4 | 13 | M1, M4 |
| GSE21138 | PFC | - | 11 | - |
| GSE53987 | PFC/hippo/striatum | - | 6 | - |
| GSE12649 | PFC (mito) | - | 5 | - |

Hub genes per module are ranked by intra-modular connectivity (kME). Notable hub genes:

**GSE38484:** BNIP2, CAB39, SMEK2, NKG7, TMED5, PPP2CA, SNRK, DOCK11, VPS4B

**GSE27383:** SELENBP1, PRKAR2B, TUBB1, PARP9, RRM2, **SNCA**, PGLYRP1, CST7, CHI3L1, WDFY3

*SNCA (alpha-synuclein) appearing as a hub gene in GSE27383 is notable given its roles in both Parkinson's disease and schizophrenia spectrum disorders.*

---

### Stage 4 - Risk Loci Mapping

Cross-referenced DE genes and module hub genes against two curated reference sets:
- **PGC3 GWAS** (Trubetskoy et al. 2022): 113 prioritised genes from genome-wide significant loci
- **Family/candidate study genes**: 41 genes including CHRNA7, DISC1, NRG1, DTNBP1, COMT, CACNA1C, ZNF804A, C4A, SETD1A

```
High-evidence genes (DE + hub + risk locus): 97 genes across 5 datasets
Notable: SP4, SETD1A, FURIN, FBXO11, VRK2, PRF1
```

GSE12649 hub genes with risk locus overlap: NTRK2, CNP (both myelin/neurotrophic - relevant to mitochondrial dysfunction focus of that dataset).

---

### Stage 5 - Pathway Enrichment

GSEA preranked (t-statistic as ranking metric) against KEGG, GO Biological Process, and Reactome via gseapy.

**Selected significant pathways (FDR < 0.05):**

| Pathway | Dataset | NES | FDR |
|---------|---------|-----|-----|
| Immune system | GSE38484 | 2.14 | 0.001 |
| Neutrophil degranulation | GSE38484 | 1.98 | 0.003 |
| Synapse assembly | GSE27383 | -1.87 | 0.012 |
| Glutamatergic synapse | GSE27383 | -1.74 | 0.028 |
| Complement cascade | GSE21138 | 1.66 | 0.041 |
| mRNA splicing | GSE38484 | -1.61 | 0.045 |
| Oxidative phosphorylation | GSE53987 | - | - |
| Mitochondrial metabolism | GSE12649 | - | - |

GSE53987 produced 193 significant KEGG pathways and 1,451 significant GO Biological Process terms (FDR < 0.25), with strong signal in metabolic and synaptic categories. GSE12649's mitochondrial focus is reflected in enrichment of oxidative phosphorylation and related pathways.

---

### Stage 6 - Module Preservation (Cross-dataset Validation)

Zsummary statistic (Langfelder & Horvath 2011) measures whether co-expression structure in the reference dataset (GSE38484 blood) is maintained in test datasets. Z > 10 = highly preserved; Z = 2-10 = moderately preserved; Z < 2 = not preserved.

```
Module preservation: GSE38484 (blood) → GSE27383 (PBMC)
─────────────────────────────────────────────────────────
  M1   n=57   Zsummary=16.2  ████████████████  HIGHLY PRESERVED
  M3   n=40   Zsummary=14.9  ███████████████   HIGHLY PRESERVED
  M6   n=442  Zsummary=15.0  ███████████████   HIGHLY PRESERVED
  M9   n=3525 Zsummary=16.4  ████████████████  HIGHLY PRESERVED

Module preservation: GSE38484 (blood) → GSE21138 (brain)
─────────────────────────────────────────────────────────
  M9   n=3525 Zsummary=8.2   ████████          Moderately preserved
  All others  Zsummary<2     Not preserved
```

Modules M1, M3, M6, and M9 show strong blood-to-blood preservation. The lack of blood-to-brain preservation is expected (different cell types, tissue-specific co-expression programs).

---

### Stage 7 - Cell Type Deconvolution

MCPcounter-style marker gene scoring applied to all datasets. Z-scored expression of published blood cell type markers (7-10 markers per cell type).

**GSE38484 (whole blood) - significant differences:**

```
Cell type       SCZ score    Ctrl score   logFC    FDR
─────────────────────────────────────────────────────
NK cells          -0.147       +0.163     -0.31   0.001  *** lower in SCZ
Platelets         -0.121       +0.133     -0.25   0.031  *   lower in SCZ
CD8 T cells       -0.119       +0.131     -0.25   0.031  *   lower in SCZ
```

**GSE27383 (PBMC) - replication:**

```
Cell type       SCZ score    Ctrl score   logFC    FDR
─────────────────────────────────────────────────────
CD8 T cells       -0.203       +0.301     -0.50   0.007  **  REPLICATED
NK cells          -0.247       +0.366     -0.61   0.010  *   REPLICATED
```

**Finding:** CD8 cytotoxic T cells and NK cells are consistently reduced in SCZ patients compared to controls, replicating across two independent blood datasets. This aligns with immune dysfunction hypotheses in schizophrenia.

GSE21138, GSE53987, and GSE12649 (brain tissue): no significant cell type differences detected - expected, as markers were designed for blood.

---

### Stage 8 - PPI Network Analysis

Hub genes and DE risk genes queried against STRING DB (interaction confidence >= 700). Network metrics computed: degree, betweenness centrality, clustering coefficient.

```
GSE38484 - Blood PPI: 73 nodes, ribosomal protein cluster
  Top hubs: RPL17, RPL23, RPL27 (ribosomal biogenesis)

GSE27383 - PBMC PPI: 36 nodes, immune/cytotoxic cluster
  Top hubs: TBX21 (T-bet), IL2RB, PRF1 (perforin)
  Key: TBX21-PRF1 axis links to NK/CD8 deconvolution finding

GSE21138 - Brain PPI: 8 nodes, complement cluster
  Top hubs: LAPTM5, C1QA, C1QB

GSE12649 - Brain PPI: 4 nodes (small network, few sig DE genes)
  Notable: NTRK2, CNP (myelin integrity genes)
```

---

### Stage 9 - Drug Repurposing (CMap/LINCS)

GSEA preranked against 6 drug perturbation libraries from Enrichr:
- `LINCS_L1000_Chem_Pert_Consensus_Sigs` (~10,850 perturbations)
- `Drug_Perturbations_from_GEO_down/up`
- `Old_CMAP_down/up` (original Connectivity Map)
- `DrugMatrix` (toxicogenomics)

Drugs with negative NES reverse the disease signature and are scored as repurposing candidates.

**Methodology validation** - known antipsychotics correctly recover in all blood datasets:

```
Drug             Dataset       NES      Note
────────────────────────────────────────────────────
Haloperidol      Blood/38484  -2.20    Reverses SCZ sig  ✓
Clozapine        Blood/38484  -2.09    Reverses SCZ sig  ✓
Risperidone      Blood/38484  -2.62    Reverses SCZ sig  ✓
Thioridazine     PBMC/27383   -2.13    Reverses SCZ sig  ✓
```

**Cross-dataset repurposing candidates** (replicate across 2+ datasets):

```
Rank  Drug              Mean NES   Datasets  Note
──────────────────────────────────────────────────────────────────
  1   fluoxetine        -3.23      2         SSRI; adjunct SCZ use documented
  2   creatine          -2.95      2         Energy metabolism; neuroprotective ★
  3   d-serine          -2.94      2         NMDA co-agonist; active trials ★★
  4   isoflurane        -2.63      2         Anaesthetic; NMDA modulation
  5   Glipizide         -3.22      1 (brain) Sulfonylurea; metabolic pathway ★
  6   Hesperidin        -2.17      3 (orig)  Citrus flavonoid; anti-inflammatory
  7   Amantadine        -2.01      3 (orig)  NMDA antagonist; dopamine releaser ★
```

★ = mechanistically plausible for SCZ &nbsp;&nbsp; ★★ = active clinical trial evidence

**Creatine** emerging as a top brain-signature reversal candidate is consistent with the mitochondrial dysfunction hypothesis (GSE12649). **D-Serine** replicates across both new brain datasets (GSE53987 and GSE12649) supporting the hypoglutamatergic / NMDA co-agonist deficit model.

**Curcumin** (NES=-1.86, libs=2) and **luteolin** emerge from the GSE12649 mitochondrial dataset, both with established anti-inflammatory and mitochondria-protective properties.

---

### Stage 10 - Medication Dose-Response & Blood-Brain Confounding

**Part B - Dose-response (GSE21138 brain, n=27 medicated SCZ patients):**

Drug dose range: 50-750 mg chlorpromazine equivalents across 10 antipsychotic types. Top dose-correlated genes (Spearman rho, uncorrected - underpowered at n=27):

```
Gene       Spearman rho   Direction
────────────────────────────────────
DSCAML1      +0.712       increases
BIN2         -0.705       decreases
TGM6         -0.677       decreases
DACH1        +0.658       increases
NALCN        +0.647       increases
```

No genes reached FDR < 0.05 (underpowered at n=27).

**Part C - Blood-brain confounding:** 0 of the 4,777 blood DE genes are significantly dose-responsive in brain (FDR < 0.05). Blood DE genes classified as likely disease markers. Risk genes including **TCF4**, **NRG1**, **HTR2A**, and **NR3C1** validated as dose-independent signals.

---

## Metabolic / Ketogenic Evidence

A separate evidence track examines metabolic and ketogenic interventions in schizophrenia, motivated by:
- Energy metabolism pathways enriched in GSE53987 and GSE12649
- Creatine and Glipizide emerging from computational drug repurposing
- An emerging body of clinical trial evidence (10+ registered trials)

Key mechanistic overlaps with the pipeline findings:

| Mechanism | Pipeline overlap |
|-----------|-----------------|
| Mitochondrial bioenergetics | GSE12649 hub genes (NTRK2, CNP), pathway enrichment |
| NMDA/glutamate | d-serine top cross-dataset candidate |
| Neuroinflammation | NK/CD8 deconvolution, complement PPI cluster |
| Oxidative stress | GSE53987 pathway enrichment |

The metabolic tab in the dashboard tracks clinical trial progress, mechanistic evidence, and combination protocol data (antipsychotics + KD + L-methylfolate).

---

## Convergent Evidence Summary

The pipeline converges on several biological themes across independent lines of evidence:

### Immune/Inflammatory Dysregulation
- NK cells and CD8 T cells reduced in SCZ blood (GSE38484 + GSE27383, replicated)
- TBX21-PRF1 cytotoxic network disrupted (PPI, GSE27383)
- Complement cluster (C1QA/C1QB) altered in brain (PPI, GSE21138)
- Anti-inflammatory drugs (hesperidin, curcumin, luteolin) reverse SCZ signature

### Glutamatergic/NMDA Pathway
- D-serine top cross-brain-dataset candidate (NMDA co-agonist)
- Amantadine (NMDA antagonist) cross-replicates in blood datasets
- Glutamatergic synapse pathway downregulated (GSEA, GSE27383)

### Mitochondrial/Metabolic
- Creatine reversal signal in both brain datasets (NES=-2.95)
- Glipizide (sulfonylurea, glucose metabolism) top brain candidate
- Oxidative phosphorylation enriched in GSE53987 and GSE12649
- Mitochondrial focus of GSE12649 confirms mito-related hub genes

### Risk Gene Convergence
97 high-evidence genes satisfy DE + hub gene + PGC3/family risk locus criteria across 5 datasets.
Top convergent genes: **SETD1A**, **TCF4**, **FOXP1**, **FURIN**, **VRK2**, **SP4**

---

## Stage 11 (exploratory) — MAMMAL Cross-Modal Drug Scoring

A scout experiment testing whether IBM's MAMMAL biomedical foundation model
([Shoshan et al., 2026, *npj Drug Discovery*](https://www.nature.com/articles/s44386-026-00047-4)) can complement Stage 9's classical GSEA-CMap drug repurposing
with cross-modal (protein + small-molecule) reasoning. MAMMAL is a 458M-parameter
multi-task transformer trained on 2 billion biological samples (UniProt + PubChem
+ ZINC + STRING + CELLxGENE + OAS).

**Hypothesis (going in):** MAMMAL's drug-target binding affinity head could
rank antipsychotics correctly against canonical receptors (e.g. dopamine D2),
in which case it would provide a target-driven scorer to complement Stage 9's
signature-similarity ranking.

### Scout result — NO-GO (zero-shot, DRD2)

A six-drug panel (haloperidol, clozapine, risperidone vs aspirin, paracetamol,
ibuprofen) was scored against dopamine D2 receptor (UniProt P14416) using
`ibm/biomed.omics.bl.sm.ma-ted-458m.dti_bindingdb_pkd`.

```
drug         label     pKd
risperidone  positive  6.298
haloperidol  positive  6.231
ibuprofen    negative  6.211      <-- ranks above clozapine
clozapine    positive  6.210
aspirin      negative  6.192
paracetamol  negative  6.184

Mean(positive) - Mean(negative) = 0.05  (threshold for GO: 1.0)
```

Zero-shot MAMMAL does not cleanly recover the canonical antipsychotic-DRD2
relationship. A canonical-input sanity check (MAMMAL's own example: 50-aa
peptide + melatonin → pKd 5.49) confirmed the inference path is correct,
so the failure is real, not a wiring bug.

### Interpretation

The model produced distinct target-level priors (5.5 for the canonical 50-aa
peptide vs 6.2 for DRD2) but did not discriminate drugs within DRD2. Likely
cause: BindingDB-pKd's training set is dominated by kinase and protease
ligand data; DRD2 (an aminergic GPCR) is under-represented, and the released
fine-tune lacks resolution on this receptor class.

### Route #1 follow-up — multi-target GPCR scout (also NO-GO)

Same 6-drug panel applied to DRD3 (P35462), 5-HT2A (P28223), 5-HT1A (P08908)
in addition to DRD2. All four targets failed:

| Target | Margin | Verdict |
|--------|--------|---------|
| DRD2   | +0.05  | NO-GO   |
| DRD3   | +0.03  | NO-GO   |
| 5-HT2A | +0.02  | NO-GO   |
| 5-HT1A | +0.04  | NO-GO   |

Ibuprofen ranks above clozapine on three of four targets. The failure is
**general across aminergic GPCRs**, not DRD2-specific. The released DTI head
has learned target-level priors but no within-target drug discrimination.
Full results: [`docs/STAGE11-ROUTE1-RESULTS.md`](docs/STAGE11-ROUTE1-RESULTS.md).

### What this rules in / out

- ❌ **The released DTI-head approach is not viable** for zero-shot
  psychiatric drug repurposing on aminergic GPCRs.
- ❌ **The originally-scoped Stage 11 (drug × bulk gene expression scoring)
  is not buildable from public artefacts.** The cancer-drug-response head
  used in the paper's carfilzomib result was not released.
- ✓ **Not yet falsified:** MAMMAL embeddings + a thin classifier (route #2),
  psychiatric-ligand fine-tune (route #3), generation-mode tasks like
  novel-candidate design for SETD1A/TCF4 (route #4 — paper's strongest
  published task), kinase/protease targets (different class than tested).

### Repro

```bash
pip install -r requirements-mammal.txt          # Python 3.10-3.12 required
python -m pipeline.stage11_mammal_scout
```

Outputs `results/stage11_scout_scores.csv` and `results/stage11_scout_verdict.txt`.
Model (~2GB) auto-downloads from Hugging Face on first run.

See [`docs/STAGE11.md`](docs/STAGE11.md) for the full Stage 11 design,
risk register, and publication-angle notes.

---

## Web Dashboard

A live interactive dashboard is deployed at [schizophrenia-genomics.vercel.app](https://schizophrenia-genomics.vercel.app).

**Stack:**
- **Frontend:** Next.js 15, TanStack Query, Recharts
- **Backend:** FastAPI + DuckDB (464K rows, 23 tables)
- **RAG query:** ChromaDB (1,480 embedded chunks) + Ollama nomic-embed-text + Claude
- **Hosting:** Vercel (frontend) + Vultr Sydney VPS (API, port 8003)

**Tabs:** Overview · Pipeline · Datasets · Genes · Modules · Pathways · Drugs · Metabolic · Query

The Query tab supports natural language questions grounded in the pipeline results (e.g. "Which genes are consistently dysregulated across blood and brain?", "What drug candidates target glutamate pathways?").

To run the dashboard locally:

```bash
cd website/dashboard
npm install
npm run dev         # Frontend at localhost:3000

cd website/
uvicorn api.main:app --port 8001  # API at localhost:8001
```

To rebuild the DuckDB and ChromaDB indexes:

```bash
cd website/
python -m query.build_index --phase 1 --fresh   # DuckDB ingest
python -m query.build_index --phase 3           # ChromaDB embed (requires Ollama)
```

---

## File Structure

```
schizophrenia-genomics/
├── run.py                              # Entry point
├── config.py                           # Paths, parameters, dataset configs
├── requirements.txt                    # Python dependencies
│
├── pipeline/
│   ├── utils.py                        # Shared logging, I/O, plotting
│   ├── stage1_download.py              # GEO download + probe-to-gene mapping
│   ├── stage2_diffexpr.py              # Differential expression + meta-analysis
│   ├── stage3_coexpression.py          # WGCNA-style co-expression networks
│   ├── stage4_risk_loci.py             # PGC3 + family gene cross-reference
│   ├── stage5_pathways.py              # GSEA + pathway visualisation
│   ├── stage6_module_preservation.py   # Zsummary cross-dataset validation
│   ├── stage7_deconvolution.py         # MCPcounter-style cell type scoring
│   ├── stage8_ppi.py                   # STRING DB PPI network analysis
│   ├── stage9_drug_repurposing.py      # CMap/LINCS drug repurposing
│   └── stage10_family_medication.py    # Dose-response + blood-brain confounding
│
├── reference/
│   ├── pgc3_risk_genes.csv             # 113 genes from PGC3 GWAS
│   ├── family_study_genes.csv          # 41 candidate/family study genes
│   ├── ketogenic_studies.csv           # 10 KD clinical trials
│   ├── ketogenic_mechanisms.csv        # 7 mechanistic pathways
│   └── additional_datasets.csv        # 13 candidate datasets catalogued
│
├── website/
│   ├── api/                            # FastAPI backend
│   ├── dashboard/                      # Next.js frontend
│   ├── query/                          # RAG + DuckDB query engine
│   ├── Dockerfile
│   └── requirements.txt
│
├── data/
│   ├── raw/                            # Cached GEO SOFT files
│   └── processed/                      # Expression matrices + phenotypes
│
├── results/                            # All CSV outputs (~97 files, gitignored)
└── figures/                            # All plots at 300 DPI (~50 PNG files, gitignored)
```

---

## Usage

### Prerequisites

```bash
pip install -r requirements.txt
```

Core dependencies: `GEOparse`, `gseapy`, `scipy`, `statsmodels`, `fastcluster`, `networkx`, `matplotlib`, `seaborn`, `adjustText`. No R required. No access-controlled data required.

### Running the pipeline

```bash
# Full pipeline on all 5 datasets
python run.py --datasets GSE38484,GSE27383,GSE21138,GSE53987,GSE12649

# Specific stages
python run.py --stages 1,2,3,4,5
python run.py --stages 6,7,8,9,10

# Single stage on a specific dataset
python run.py --stages 2 --datasets GSE38484
python run.py --stages 9 --datasets GSE27383,GSE38484

# Re-run from stage 3 (skip download, use cached)
python run.py --stages 3,4,5,6,7,8,9,10

# New datasets only (stages 3+ after download and DE are complete)
python run.py --stages 3,5,7,8,9,10 --datasets GSE53987,GSE12649 --primary GSE53987
```

Stage 1 downloads ~350MB of GEO data and caches it. All subsequent stages run from cached files.

### Expected runtimes (approximate, 5 datasets)

```
Stage 1  (download)         ~ 10-25 min  (network-dependent)
Stage 2  (DE + meta)        ~ 4-5 min
Stage 3  (co-expression)    ~ 15-25 min  (TOM computation)
Stage 4  (risk loci)        ~ 2 min
Stage 5  (pathways/GSEA)    ~ 10-20 min  (Enrichr API calls)
Stage 6  (preservation)     ~ 3-5 min    (permutation testing)
Stage 7  (deconvolution)    ~ 1-2 min
Stage 8  (PPI/STRING)       ~ 1-2 min    (STRING API calls)
Stage 9  (drug repurposing) ~ 40-60 min  (GSEA × 6 libraries × 5 datasets)
Stage 10 (dose-response)    ~ 1 min
```

---

## Limitations

1. **No single-cell resolution.** Bulk RNA-seq and microarray data conflate cell-type-specific signals. Cell type deconvolution (Stage 7) partially addresses this but uses proxy marker scores.

2. **Medication confounding.** All datasets contain patients on antipsychotics. The dose-response analysis uses n=27 from a single brain dataset - underpowered for definitive confounding attribution.

3. **No family-structured data.** Public GEO contains no family-discordant blood expression data for schizophrenia. The paired analysis framework (Stage 10, Part A) is implemented but awaits suitable data from dbGaP.

4. **Drug repurposing is hypothesis-generating.** CMap/LINCS signatures are primarily from cancer cell lines, not brain or blood tissue. Candidates require experimental validation.

5. **Array platforms differ.** GSE38484 (Illumina HT-12), GSE27383/GSE21138/GSE53987 (Affymetrix HG-U133+2), GSE12649 (Affymetrix HG-U133A) use different probe sets. Meta-analysis restricted to common genes (7,797 of ~25,000).

6. **Brain datasets are underpowered individually.** GSE21138 (n=59), GSE53987 (n=103 across 3 regions), and GSE12649 (n=69) each yield few individually FDR-significant genes. Their contribution is through meta-analysis and module/pathway analysis rather than standalone DE.

7. **Preliminary status.** This pipeline has not been peer-reviewed. All findings should be treated as computational hypotheses requiring independent replication and experimental validation.

---

## References

- Trubetskoy, V. et al. (2022). Mapping genomic loci implicates genes and synaptic biology in schizophrenia. *Nature*, 604, 502-508. [PGC3 GWAS]
- Langfelder, P. & Horvath, S. (2008). WGCNA: an R package for weighted correlation network analysis. *BMC Bioinformatics*, 9, 559.
- Langfelder, P. & Horvath, S. (2011). Is my network module preserved and reproducible? *PLoS Computational Biology*, 7(1).
- Lamb, J. et al. (2006). The Connectivity Map. *Science*, 313, 1929-1935.
- Subramanian, A. et al. (2017). A Next Generation Connectivity Map. *Cell*, 171, 1437-1452. [LINCS L1000]
- Becht, E. et al. (2016). Estimating the population abundance of tissue-infiltrating immune and stromal cell populations using gene expression. *Genome Biology*, 17, 218. [MCPcounter]
- Roffman, J.L. et al. (2018). Randomized multicenter investigation of folate plus vitamin B12 supplementation in schizophrenia. *JAMA Psychiatry*, 75(8), 794-802. [L-methylfolate]
- Galvin, R. (2020). *Hidden Valley Road: Inside the Mind of an American Family*. Doubleday.
