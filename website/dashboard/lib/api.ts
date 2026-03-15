const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

// Stats
export const fetchStats = () => get<Stats>("/api/stats");

// Datasets
export const fetchDatasets = () => get<DatasetSummary[]>("/api/datasets");
export const fetchDatasetDE = (id: string, padj = 0.05, limit = 200) =>
  get<DEGene[]>(`/api/datasets/${id}/de?padj_max=${padj}&limit=${limit}`);
export const fetchDatasetModules = (id: string) =>
  get<Module[]>(`/api/datasets/${id}/modules`);
export const fetchDatasetHubGenes = (id: string, module?: string) =>
  get<HubGene[]>(`/api/datasets/${id}/hub_genes${module ? `?module=${module}` : ""}`);
export const fetchDatasetRiskOverlap = (id: string) =>
  get<RiskGene[]>(`/api/datasets/${id}/risk_overlap`);
export const fetchDatasetPathways = (id: string, library?: string, fdr = 0.05) =>
  get<GSEAResult[]>(`/api/datasets/${id}/pathways?fdr_max=${fdr}${library ? `&library=${library}` : ""}`);
export const fetchDatasetCellTypes = (id: string) =>
  get<CellType[]>(`/api/datasets/${id}/cell_types`);
export const fetchDatasetPPI = (id: string) =>
  get<PPIData>(`/api/datasets/${id}/ppi`);
export const fetchDatasetDrugs = (id: string, fdr = 0.25) =>
  get<DrugCandidate[]>(`/api/datasets/${id}/drugs?fdr_max=${fdr}`);

// Genes
export const fetchGenes = (limit = 200, sort = "combined_padj") =>
  get<GeneSummary[]>(`/api/genes?limit=${limit}&sort=${sort}`);
export const fetchGene = (gene: string) => get<GeneDetail>(`/api/genes/${gene}`);

// Drugs
export const fetchCrossDatasetDrugs = (minDatasets = 2) =>
  get<CrossDrug[]>(`/api/drugs/cross_dataset?min_datasets=${minDatasets}`);
export const fetchValidatedDrugs = () => get<CrossDrug[]>("/api/drugs/validated");
export const fetchCandidateDrugs = () => get<CrossDrug[]>("/api/drugs/candidates");
export const fetchConfounding = () => get<ConfoundingData>("/api/drugs/confounding");

// Pathways
export const fetchGSEA = (dataset?: string, library?: string, fdr = 0.05, limit = 100) =>
  get<GSEAResult[]>(`/api/pathways/gsea?fdr_max=${fdr}&limit=${limit}${dataset ? `&dataset_id=${dataset}` : ""}${library ? `&library=${library}` : ""}`);
export const fetchSCZPathways = () => get<SCZPathway[]>("/api/pathways/scz_specific");
export const fetchPreservation = () => get<Preservation[]>("/api/pathways/preservation");

// Modules
export const fetchModuleEnrichment = (dataset?: string, module?: string) =>
  get<ModuleEnrichment[]>(`/api/pathways/modules?limit=50${dataset ? `&dataset_id=${dataset}` : ""}${module ? `&module=${module}` : ""}`);

// Figures
export const fetchFigures = () => get<Figure[]>("/api/figures");

// Query
export const runQuery = (query: string, datasetId?: string) =>
  post<QueryResult>("/api/query", { query, dataset_id: datasetId, stream: false });

// Types
export interface Stats {
  n_datasets: number;
  n_genes_tested: number;
  n_meta_sig_genes: number;
  n_high_evidence_genes: number;
  n_drug_candidates: number;
  n_preserved_modules: number;
  n_validated_antipsychotics: number;
  n_pipeline_stages: number;
  de_by_dataset: { dataset_id: string; n_sig: number; n_up: number; n_down: number }[];
  top_cross_drugs: CrossDrug[];
}

export interface DatasetSummary {
  dataset_id: string;
  tissue: string;
  platform: string;
  n_scz: number;
  n_ctrl: number;
  n_de_genes: number;
  n_modules: number;
  n_hub_genes: number;
  n_risk_overlaps: number;
  n_drug_candidates: number;
}

export interface DEGene {
  gene: string;
  logFC: number;
  mean_SCZ: number;
  mean_control: number;
  stat: number;
  pvalue: number;
  padj: number;
}

export interface Module {
  module: string;
  correlation: number;
  pvalue: number;
  n_samples: number;
  n_genes: number;
  risk_genes_count: number;
  fraction_risk: number;
}

export interface HubGene {
  gene: string;
  module: string;
  kME: number;
  kME_signed: number;
}

export interface RiskGene {
  gene: string;
  logFC: number;
  padj: number;
  is_significant: boolean;
  in_PGC3: boolean;
  in_family_study: boolean;
  source: string;
}

export interface GSEAResult {
  dataset_id?: string;
  gene_set_library: string;
  term: string;
  ES: number;
  NES: number;
  nom_pval: number;
  fdr_qval: number;
  lead_genes: string;
}

export interface CellType {
  cell_type: string;
  mean_score_SCZ: number;
  mean_score_ctrl: number;
  logFC: number;
  stat: number;
  pvalue: number;
  padj: number;
}

export interface PPINode {
  gene: string;
  degree: number;
  degree_centrality: number;
  betweenness: number;
  eigenvector: number;
  is_DE: boolean;
  logFC: number;
  is_hub: boolean;
  is_risk: boolean;
}

export interface PPIEdge { gene_a: string; gene_b: string; score: number; }
export interface PPIData { nodes: PPINode[]; edges: PPIEdge[]; }

export interface DrugCandidate {
  drug_name: string;
  mean_NES: number;
  min_FDR: number;
  n_libraries: number;
  best_term: string;
  is_known_psychiatric: boolean;
  is_repurposing_interest: boolean;
  composite_score: number;
}

export interface CrossDrug {
  drug_name: string;
  n_datasets: number;
  mean_NES: number;
  best_FDR: number;
  is_known: boolean;
  is_repurpose: boolean;
  datasets?: string;
}

export interface ConfoundingData {
  report: { dataset: string; confounding_risk: string; note: string }[];
  flagged_genes: object[];
}

export interface GeneSummary {
  gene: string;
  mean_logFC: number;
  combined_padj: number;
  direction_consistent: boolean;
  n_datasets: number;
  evidence_count: number | null;
  is_DE: boolean | null;
  is_hub: boolean | null;
  is_risk_gene: boolean | null;
}

export interface GeneDetail {
  gene: string;
  de_results: object[];
  meta: object | null;
  hub_genes: object[];
  module_membership: object[];
  risk_overlap: object[];
  high_evidence: object | null;
  ppi_neighbors: object[];
  dose_response: object | null;
}

export interface SCZPathway { term: string; gene_set: string; NES: number; FDR: number; pvalue: number; n_genes: number; }
export interface Preservation { ref_dataset: string; test_dataset: string; module: string; n_genes_ref: number; n_genes_common: number; Zsummary: number; }
export interface ModuleEnrichment { dataset_id: string; gene_set: string; term: string; overlap: string; pvalue: number; adjusted_pvalue: number; odds_ratio: number; combined_score: number; module: string; }
export interface Figure { filename: string; stem: string; size: number; }

export interface QueryResult {
  query: string;
  classification: { type: string; dataset_id: string | null; gene: string | null; confidence: number };
  sql: string;
  sql_method: string;
  sql_results: Record<string, unknown>[] | null;
  chunks: { text: string; metadata: Record<string, string>; score: number }[];
  answer: string;
  evidence_tiers: string[];
}
