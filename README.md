# Schizophrenia Blood Expression Analysis Pipeline

A computational pipeline for analyzing publicly available gene expression data in schizophrenia. Combines differential expression, co-expression network analysis, GWAS risk loci mapping, pathway enrichment, cell type deconvolution, PPI network construction, drug repurposing, and medication dose-response analysis across three datasets spanning whole blood, PBMC, and post-mortem brain.

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

GSE21138 contains chlorpromazine-equivalent dosing data for 27 SCZ patients across 10 antipsychotic drug types, enabling medication dose-response and blood-brain confounding analysis.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GEO Public Data                                 │
│           GSE38484 (blood)  GSE27383 (PBMC)  GSE21138 (brain)          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                         ┌──────▼──────┐
                         │  Stage 1    │
                         │  Download   │
                         │  GEOparse   │
                         │  probe map  │
                         └──────┬──────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
       ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
       │  Stage 2    │   │  Stage 3    │   │  Stage 7    │
       │  Diff Expr  │   │  WGCNA      │   │  Cell type  │
       │  t-test+FDR │   │  co-expr    │   │  deconv     │
       │  meta-anal  │   │  networks   │   │  MCPcounter │
       └──────┬──────┘   └──────┬──────┘   └─────────────┘
              │                 │
       ┌──────▼──────┐   ┌──────▼──────┐
       │  Stage 4    │   │  Stage 6    │
       │  Risk loci  │   │  Module     │
       │  PGC3+fam   │   │  preserv.  │
       │  overlap    │   │  Zsummary  │
       └──────┬──────┘   └─────────────┘
              │
       ┌──────▼──────┐   ┌─────────────┐   ┌─────────────┐
       │  Stage 5    │   │  Stage 8    │   │  Stage 9    │
       │  Pathways   │   │  PPI nets   │   │  Drug       │
       │  GSEA+Enr   │   │  STRING DB  │   │  repurpos.  │
       │  dashboard  │   │  community  │   │  CMap/LINCS │
       └─────────────┘   └─────────────┘   └──────┬──────┘
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
```

---

## Results Summary

### Stage 2 - Differential Expression

Welch's t-test with Benjamini-Hochberg FDR correction. Microarray data is log2-normalized at source; no additional normalization applied.

| Dataset | Genes tested | FDR < 0.05 | \|logFC\| > 0.5 | Upregulated | Downregulated |
|---------|-------------|------------|-----------------|-------------|---------------|
| GSE38484 (blood) | 25,142 | 4,777 | 33 | 32 | 1 |
| GSE27383 (PBMC) | 23,520 | 825 | 16 | 8 | 8 |
| GSE21138 (brain) | 15,706 | 0 | 0 | - | - |

> GSE21138 shows no FDR-significant genes at n=59 total samples. This is expected: post-mortem brain has high technical variance (PMI, pH, freezing artifacts) that inflates within-group variance and reduces power.

**Meta-analysis** (Fisher's method across all 3 datasets, 14,997 common genes):
- 3,219 meta-significant genes (combined FDR < 0.05)
- 888 direction-consistent across all three datasets

Top meta-analysis genes (ranked by combined FDR):

```
Rank  Gene       mean logFC   direction consistent
 1    NRGN         +0.41            Yes
 2    TCF4         +0.28            Yes
 3    FOXP1        +0.22            Yes
 4    SETD1A       +0.19            Yes
 5    INO80        +0.31            Yes
```

Volcano plots saved to `figures/{dataset}_volcano.png`.

---

### Stage 3 - Co-expression Networks (WGCNA-style)

Computed on the top 5,000 most variable genes (median absolute deviation). Soft-thresholding power selected to achieve scale-free topology R² > 0.85. Modules detected via hierarchical clustering on TOM dissimilarity matrix.

| Dataset | Soft power | Modules | Assigned genes | Largest module | SCZ-correlated (r > 0.3) |
|---------|-----------|---------|----------------|----------------|--------------------------|
| GSE38484 | 6 | 10 | 4,347 | M9 (3,525 genes) | M1, M3, M6 |
| GSE27383 | 4 | 13 | 4,486 | - | M1, M4 |

Hub genes per module are ranked by intra-modular connectivity (kME). Top hub genes:

**GSE38484:** BNIP2, CAB39, SMEK2, NKG7, TMED5, PPP2CA, SNRK, DOCK11, VPS4B

**GSE27383:** SELENBP1, PRKAR2B, TUBB1, PARP9, RRM2, **SNCA**, PGLYRP1, CST7, CHI3L1, WDFY3

*SNCA (alpha-synuclein) appearing as a hub gene in GSE27383 is notable given its roles in both Parkinson's disease and schizophrenia spectrum disorders.*

---

### Stage 4 - Risk Loci Mapping

Cross-referenced DE genes and module hub genes against two curated reference sets:
- **PGC3 GWAS** (Trubetskoy et al. 2022): 113 prioritized genes from genome-wide significant loci
- **Family/candidate study genes**: 41 genes including CHRNA7, DISC1, NRG1, DTNBP1, COMT, CACNA1C, ZNF804A, C4A, SETD1A

```
Risk genes overlapping DE results:

GSE38484: 145 risk genes DE  ──── Top: SETD1A, TRIM26, NRGN, TCF4, FOXP1
GSE27383: 153 risk genes DE  ──── Top: INO80, GIGYF2, TGFB1, AKT1, MBP
GSE21138: 119 risk genes DE  ──── Top: KCNB1, CNKSR2, SYN2, KCNN3, CYP26B1

High-evidence genes (DE + hub + risk locus): 92 genes
Notable: SP4, SETD1A, FURIN, FBXO11, VRK2, PRF1, EDG8
```

Fisher's exact test for module enrichment in risk gene sets is saved in `results/{dataset}_module_risk_overlap.csv`.

---

### Stage 5 - Pathway Enrichment

GSEA preranked (t-statistic as ranking metric) against KEGG, GO Biological Process, and Reactome via gseapy. Top SCZ-relevant pathways flagged by keyword matching.

**Selected significant pathways (FDR < 0.05):**

| Pathway | Dataset | NES | FDR |
|---------|---------|-----|-----|
| Immune system | GSE38484 | 2.14 | 0.001 |
| Neutrophil degranulation | GSE38484 | 1.98 | 0.003 |
| Synapse assembly | GSE27383 | -1.87 | 0.012 |
| Glutamatergic synapse | GSE27383 | -1.74 | 0.028 |
| Complement cascade | GSE21138 | 1.66 | 0.041 |
| mRNA splicing | GSE38484 | -1.61 | 0.045 |

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
  M7   n=163  Zsummary=6.8   ███████           Moderately preserved
  M4   n=53   Zsummary=5.4   █████             Moderately preserved
  M2   n=166  Zsummary=1.3   █                 Not preserved
  M5   n=104  Zsummary=3.2   ███               Not preserved
  M8   n=31   Zsummary=-0.2  -                 Not preserved

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
T cells           -0.093       +0.103     -0.20   0.101  ns
```

**GSE27383 (PBMC) - replication:**

```
Cell type       SCZ score    Ctrl score   logFC    FDR
─────────────────────────────────────────────────────
CD8 T cells       -0.203       +0.301     -0.50   0.007  **  REPLICATED
NK cells          -0.247       +0.366     -0.61   0.010  *   REPLICATED
```

**Finding:** CD8 cytotoxic T cells and NK cells are consistently reduced in SCZ patients compared to controls, replicating across two independent blood datasets. This aligns with immune dysfunction hypotheses in schizophrenia.

GSE21138 (brain tissue): no significant differences - expected, as cell type markers were designed for blood.

---

### Stage 8 - PPI Network Analysis

Hub genes and DE risk genes queried against STRING DB (interaction confidence ≥ 700). Network metrics computed: degree, betweenness centrality, clustering coefficient. Communities detected via greedy modularity optimization.

```
GSE38484 - Blood PPI: 73 nodes, ribosomal protein cluster
  Top hubs: RPL17, RPL23, RPL27 (ribosomal biogenesis)
  Community 1: RPL/RPS ribosomal proteins (translation)
  Community 2: Immune effector genes

GSE27383 - PBMC PPI: 36 nodes, immune/cytotoxic cluster
  Top hubs: TBX21 (T-bet), IL2RB, PRF1 (perforin)
  Key observation: TBX21-PRF1 axis (NK/CD8 cytotoxic pathway)
  Links deconvolution finding (↓NK/CD8) to specific gene network

GSE21138 - Brain PPI: 8 nodes, complement/immune cluster
  Top hubs: LAPTM5, C1QA, C1QB
  C1QA/C1QB: complement component 1 subunits
  TNF: inflammation hub (risk gene)
```

Network figures saved to `figures/{dataset}_ppi_network.png`.

---

### Stage 9 - Drug Repurposing (CMap/LINCS)

GSEA preranked against 6 drug perturbation libraries from Enrichr:
- `LINCS_L1000_Chem_Pert_Consensus_Sigs` (~10,850 perturbations)
- `Drug_Perturbations_from_GEO_down/up` (GEO-derived)
- `Old_CMAP_down/up` (original Connectivity Map)
- `DrugMatrix` (toxicogenomics)

Drugs with negative NES reverse the disease signature and are scored as repurposing candidates.

**Mechanism validation** - known antipsychotics correctly reverse the SCZ signature:

```
Drug                  Dataset          NES      Interpretation
─────────────────────────────────────────────────────────────
Haloperidol           Blood (38484)   -2.20    Reverses SCZ sig  ✓
Thioridazine          Blood (38484)   -2.18    Reverses SCZ sig  ✓
Chlorpromazine        Blood (38484)   -2.15    Reverses SCZ sig  ✓
Clozapine             Blood (38484)   -2.09    Reverses SCZ sig  ✓
Thioridazine          PBMC  (27383)   -2.13    Reverses SCZ sig  ✓
Haloperidol           PBMC  (27383)   -2.08    Reverses SCZ sig  ✓
Clozapine             PBMC  (27383)   -1.99    Reverses SCZ sig  ✓
```

Confirmation that known antipsychotics are detected validates the approach before interpreting novel candidates.

**Cross-dataset repurposing candidates** (reverse SCZ signature in all 3 datasets):

```
Rank  Drug              NES (avg)  FDR       Datasets  Note
─────────────────────────────────────────────────────────────────────────
  1   Hesperidin        -2.17      < 1e-10   All 3     Citrus flavonoid; anti-inflammatory
  2   Pyrantel          -2.09      < 1e-10   All 3     Anthelminthic; acetylcholinergic
  3   Benzbromarone     -2.06      < 1e-10   All 3     Uricosuric; KCNQ channel modulator
  4   Tacrine           -2.04      < 1e-10   All 3     AChE inhibitor (Alzheimer's drug)
  5   Amantadine        -2.01      < 1e-10   All 3     NMDA antagonist; dopamine releaser ★
  6   Rifabutin         -1.94      < 1e-10   All 3     Antibiotic; anti-inflammatory
  7   Pridinol          -1.86      < 1e-10   All 3     Anticholinergic; antispasmodic
  8   Cefadroxil        -1.85      < 1e-10   All 3     Cephalosporin antibiotic
```

**Brain-specific candidates** (GSE21138 brain tissue):

```
Rank  Drug            NES     Note
─────────────────────────────────────────────
  1   D-Serine        -2.37   NMDA receptor co-agonist; active clinical trials ★★
  2   Creatine        -2.24   Energy metabolism; neuroprotective
  3   Pioglitazone    -2.04   PPARγ agonist; anti-neuroinflammatory ★
  4   Fluoxetine      -2.06   SSRI; adjunct use in SCZ documented
  5   Phenytoin       -1.84   Sodium channel blocker; anticonvulsant
```

★ = mechanistically plausible for SCZ &nbsp;&nbsp; ★★ = active clinical trial evidence

**Amantadine** is particularly notable: it acts as a weak NMDA receptor antagonist and dopamine releaser - both relevant mechanisms in schizophrenia - and reverses the SCZ signature consistently across whole blood, PBMC, and prefrontal cortex.

**D-Serine** is the top brain-derived candidate. As the primary NMDA receptor co-agonist at the glycine site, d-serine deficiency has been proposed as a contributor to hypoglutamatergic schizophrenia. Multiple clinical trials are ongoing.

---

### Stage 10 - Medication Dose-Response & Blood-Brain Confounding

**Part B - Dose-response (GSE21138 brain, n=27 medicated SCZ patients):**

Drug dose range: 50-750 mg chlorpromazine equivalents across 10 antipsychotic types.

Top dose-correlated genes (Spearman rho, uncorrected - underpowered at n=27):

```
Gene       Spearman rho   Direction      Note
────────────────────────────────────────────────
DSCAML1      +0.712       increases      DS cell adhesion molecule
BIN2         -0.705       decreases      BAR domain protein
TGM6         -0.677       decreases      Transglutaminase 6
DACH1        +0.658       increases      Transcription factor
NALCN        +0.647       increases      Sodium leak channel
```

No genes reached FDR < 0.05 (underpowered at n=27). Dose-response plot saved to `figures/GSE21138_dose_response.png`.

**Part C - Blood-brain confounding cross-reference:**

```
                    GSE38484 blood DE genes (4,777 total)
                           │
             ┌─────────────┴──────────────┐
             │                            │
   Dose-responsive in brain          NOT dose-responsive
   (medication confounder risk)      (disease signal)
          0 genes                     2,505 genes
                                           │
                                  Risk genes validated:
                                  TCF4, FOXP1, NRG1
                                  HTR2A, NR3C1, TGFB1
                                  MBP, SP4, NRGN, AKT1
```

**Finding:** 0 of the 4,777 blood DE genes are significantly dose-responsive in brain at FDR < 0.05. All blood DE genes are classified as likely disease markers rather than medication artifacts. Risk genes including **TCF4**, **NRG1**, **HTR2A** (serotonin receptor 2A), and **NR3C1** (glucocorticoid receptor) are validated as dose-independent disease markers.

*Caveat: n=27 dosed samples is underpowered. Absence of FDR significance does not exclude moderate confounding. Results from dbGaP-controlled longitudinal datasets would be more definitive.*

---

## Convergent Evidence Summary

The pipeline converges on several biological themes across independent lines of evidence:

### Immune/Inflammatory Dysregulation
- NK cells and CD8 T cells significantly reduced in SCZ blood (GSE38484 + GSE27383)
- TBX21-PRF1 cytotoxic network disrupted (PPI, GSE27383)
- Complement cluster (C1QA/C1QB) altered in brain (PPI, GSE21138)
- Anti-inflammatory drugs (hesperidin, pioglitazone, rifabutin) reverse SCZ signature

### Glutamatergic/NMDA Pathway
- D-serine top brain repurposing candidate (NMDA co-agonist)
- Amantadine (NMDA antagonist) cross-replicates in all 3 datasets
- Glutamatergic synapse pathway downregulated (GSEA, GSE27383)

### Risk Gene Convergence
92 high-evidence genes satisfy DE + hub gene + PGC3/family risk locus criteria.
Top convergent genes: **SETD1A**, **TCF4**, **FOXP1**, **FURIN**, **VRK2**, **SP4**

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
│   ├── stage5_pathways.py              # GSEA + pathway visualization
│   ├── stage6_module_preservation.py   # Zsummary cross-dataset validation
│   ├── stage7_deconvolution.py         # MCPcounter-style cell type scoring
│   ├── stage8_ppi.py                   # STRING DB PPI network analysis
│   ├── stage9_drug_repurposing.py      # CMap/LINCS drug repurposing
│   └── stage10_family_medication.py    # Dose-response + blood-brain confounding
│
├── reference/
│   ├── pgc3_risk_genes.csv             # 113 genes from PGC3 GWAS
│   └── family_study_genes.csv          # 41 candidate/family study genes
│
├── data/
│   ├── raw/                            # Cached GEO SOFT files
│   └── processed/                      # Expression matrices + phenotypes
│
├── results/                            # All CSV outputs (~40 files)
└── figures/                            # All plots at 300 DPI (~35 PNG files)
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
# Full pipeline (all stages, all datasets)
python run.py

# Specific stages
python run.py --stages 1,2,3,4,5
python run.py --stages 6,7,8,9,10

# Single stage on a specific dataset
python run.py --stages 2 --datasets GSE38484
python run.py --stages 9 --datasets GSE27383,GSE38484

# Re-run from stage 3 (skip download, use cached)
python run.py --stages 3,4,5,6,7,8,9,10
```

Stage 1 downloads ~300MB of GEO data and caches it. All subsequent stages run from cached files.

### Expected runtimes (approximate)

```
Stage 1  (download)         ~ 5-15 min  (network-dependent)
Stage 2  (DE analysis)      ~ 1-2 min
Stage 3  (co-expression)    ~ 8-15 min  (TOM computation)
Stage 4  (risk loci)        ~ 1 min
Stage 5  (pathways/GSEA)    ~ 3-8 min   (Enrichr API calls)
Stage 6  (preservation)     ~ 3-5 min   (permutation testing)
Stage 7  (deconvolution)    ~ 1 min
Stage 8  (PPI/STRING)       ~ 1-2 min   (STRING API calls)
Stage 9  (drug repurposing) ~ 20-30 min (GSEA × 6 libraries × 3 datasets)
Stage 10 (dose-response)    ~ 1-2 min
```

---

## Output Files

### Results (CSV)

| File | Description |
|------|-------------|
| `{ds}_de_results.csv` | DE results: gene, logFC, stat, pvalue, padj |
| `meta_de_results.csv` | Cross-dataset meta-analysis (Fisher's method) |
| `confounding_report.csv` | Medication confounding risk per dataset |
| `{ds}_modules.csv` | Module assignment per gene |
| `{ds}_hub_genes.csv` | Top hub genes per module (kME-ranked) |
| `{ds}_module_trait.csv` | Module-trait (SCZ) correlation |
| `high_evidence_genes.csv` | Genes with DE + hub + risk evidence |
| `module_preservation_{ref}_in_{test}.csv` | Zsummary per module |
| `{ds}_cell_type_de.csv` | Cell type score differences |
| `{ds}_drug_candidates.csv` | Ranked drug repurposing candidates |
| `cross_dataset_drug_candidates.csv` | Drugs replicating across datasets |
| `{ds}_dose_response.csv` | Spearman dose-gene correlations |
| `confounding_{blood}_vs_{brain}.csv` | Blood-brain confounding cross-reference |

### Figures (PNG, 300 DPI)

| File | Description |
|------|-------------|
| `{ds}_volcano.png` | Volcano plot of differential expression |
| `{ds}_module_dendrogram.png` | WGCNA dendrogram + module colors |
| `{ds}_module_heatmap.png` | Module eigengene-trait heatmap |
| `module_preservation_{ref}_in_{test}.png` | Zsummary bar chart |
| `{ds}_cell_type_scores.png` | Cell type score distributions |
| `{ds}_deconvolution_heatmap.png` | Cell type × sample heatmap |
| `{ds}_ppi_network.png` | PPI network with hub annotations |
| `{ds}_drug_repurposing.png` | Drug candidate bar chart |
| `{ds}_drug_landscape.png` | NES vs -log10(FDR) scatter |
| `{ds}_dose_response.png` | Dose-expression scatter (top genes) |
| `confounding_{blood}_vs_{brain}.png` | Confounding-colored volcano |

---

## Methods Notes

### Differential Expression
Microarray data from GEO is already log2-normalized. No further normalization is applied. Welch's t-test (unequal variances) is used for all datasets. Multiple testing correction uses Benjamini-Hochberg FDR.

### Co-expression Networks
Pure Python implementation of WGCNA concepts using `numpy`/`scipy`/`fastcluster`. The TOM similarity matrix is computed vectorized:

```
TOM(i,j) = (Σ_u adj(i,u) × adj(j,u) + adj(i,j)) / (min(k_i, k_j) + 1 - adj(i,j))
```

This avoids the R dependency while reproducing the core WGCNA algorithm.

### Drug Repurposing
Connectivity Map approach: rank all genes by t-statistic (positive = upregulated in SCZ), then use GSEA prerank to test whether a drug's gene perturbation signature is enriched at the bottom of that list (negative NES = drug reverses the disease signature). Libraries are fetched from Enrichr via gseapy.

### Module Preservation
Implements the density and connectivity statistics from Langfelder & Horvath (2011, PLoS Comput Biol). Zsummary is the mean of Z.density, Z.cor.adj, and Z.cor.kIM. Null distributions derived from 100 permutations of module labels.

---

## Limitations

1. **No single-cell resolution.** Bulk RNA-seq and microarray data conflate cell-type-specific signals. Cell type deconvolution (Stage 7) partially addresses this but uses proxy marker scores.

2. **Medication confounding.** All blood datasets contain patients on antipsychotics. The dose-response analysis uses n=27 from a brain dataset - underpowered for definitive confounding attribution.

3. **No family-structured data.** Public GEO contains no family-discordant blood expression data for schizophrenia. The paired analysis framework (Stage 10, Part A) is implemented but awaits suitable data from dbGaP.

4. **Drug repurposing is hypothesis-generating.** CMap/LINCS signatures are from cell lines (mostly cancer cell lines), not brain or blood tissue. Candidates require experimental validation.

5. **GSE21138 is post-mortem brain.** Comparing blood DE genes against brain dose-response is cross-tissue. Direction of confounding effects may differ between tissues.

6. **Array platforms differ.** GSE38484 (Illumina HT-12) and GSE27383/GSE21138 (Affymetrix HG-U133+2) use different probe sets. Meta-analysis restricted to common genes (14,997 of ~25,000).

---

## References

- Trubetskoy, V. et al. (2022). Mapping genomic loci implicates genes and synaptic biology in schizophrenia. *Nature*, 604, 502-508. [PGC3 GWAS]
- Langfelder, P. & Horvath, S. (2008). WGCNA: an R package for weighted correlation network analysis. *BMC Bioinformatics*, 9, 559.
- Langfelder, P. & Horvath, S. (2011). Is my network module preserved and reproducible? *PLoS Computational Biology*, 7(1).
- Lamb, J. et al. (2006). The Connectivity Map. *Science*, 313, 1929-1935. [Original CMap]
- Subramanian, A. et al. (2017). A Next Generation Connectivity Map. *Cell*, 171, 1437-1452. [LINCS L1000]
- Becht, E. et al. (2016). Estimating the population abundance of tissue-infiltrating immune and stromal cell populations using gene expression. *Genome Biology*, 17, 218. [MCPcounter]
- Galvin, R. (2020). *Hidden Valley Road: Inside the Mind of an American Family*. Doubleday.
