## Design Context

### Users
Researchers, bioinformaticians, and genomicists reviewing schizophrenia transcriptomics pipeline outputs. Sessions are focused and analytical - comparing gene expression across 3 GEO datasets, querying drug candidates, reading biological mechanisms. Users are comfortable with dense data but expect the interface to respect their attention.

### Brand Personality
Rigorous · Precise · Alive (the data tells a living biological story)

### Aesthetic Direction
**Editorial Scientific** - Nature magazine meets Observable notebooks. The dark mode is appropriate (scientific instrument aesthetic - think Zeiss/JEOL hardware) but it must be a *cultivated* dark: deep tinted navy-slate, never pure black. Typography hierarchy carries the design, not decoration.

**Anti-references**: Vercel/Stripe SaaS dark dashboards, gradient KPI cards, glassmorphism, purple-to-blue gradient text, identical 3-column feature grids, hero metric layouts with big colored numbers.

**References**: Nature Briefings, Observable, UCSC Genome Browser, academic data supplements.

### Design Principles
1. **Data first, chrome second** - Tables and charts are the UI. Every decorative element earns its space or gets removed.
2. **Hierarchy through type, not decoration** - Font weight, size, and spacing create hierarchy. No colored top-borders on cards, no gradient accents, no decorative glows.
3. **Tinted darks only** - Never pure black or pure gray. All surfaces and text have a subtle cool blue-slate tint (OKLCH at hue 243-250, chroma 0.007-0.018).
4. **Monospace for data, proportional for prose** - Geist Mono is for numbers, gene names, p-values, and code only. DM Sans handles all prose, labels, and navigation.
5. **Scientific precision in microcopy** - Numbers in scientific notation where appropriate. Gene names always uppercase monospace. Evidence tiers always explicit. No redundant copy.

### Font Stack
- **Display/Headings**: Instrument Serif (400 normal + italic) - scientific elegance, beautiful italics for gene names
- **Body/UI**: DM Sans (300-600) - clean geometric, clearly not Inter
- **Data**: Geist Mono - for all numeric and code content only

### Color System (OKLCH)
- Background: `oklch(11% 0.018 243)` - deep tinted navy
- Surface: `oklch(15.5% 0.016 243)` - cards/panels
- Text: `oklch(90% 0.007 245)` - cool white
- Blue accent: `oklch(64% 0.175 232)` - science blue
- Green: `oklch(66% 0.145 148)` - upregulated/replicated
- Red: `oklch(60% 0.20 23)` - downregulated/risk
- Amber: `oklch(73% 0.155 66)` - moderate/warning
- Purple: `oklch(62% 0.175 295)` - drug candidates
