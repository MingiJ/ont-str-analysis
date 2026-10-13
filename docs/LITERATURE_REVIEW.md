# Literature Review — Signal-level & Long-read STR Calling

State of the field for the thesis, as of 2026-10-13. Plain-English, with links.
Pairs with `docs/PROPOSED_RNN_ALGORITHM_PLAN.md` (our novelty claim) and
`docs/GLOSSARY.md` (terms). Use the "open frontier" and "questions" sections to
engage supervisors, panels, and the community knowledgeably.

## 1. The field has split into two regimes

**Know which one you're in** — this framing pre-empts the "why not tool X?" question.

- **Basecalled-read callers (where the field's energy now is).** Because R10.4.1
  chemistry + modern basecallers (Dorado SUP) got accurate, most 2023–2026 tools
  skip raw signal: basecall → align → genotype from the letters.
- **Signal-level / raw-squiggle callers (this thesis's niche).** A smaller, older
  subfield that works on the raw current trace. Four real members only.

## 2. The tools

### Signal-level (our comparators)
- **WarpSTR** — raw-signal DTW-like alignment to a finite-state repeat model +
  sample-level GMM genotyping. Strongest comparator here (MAE 0.722).
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC10307940/>
- **STRique** — raw-signal boundary alignment + HMM counting; also does
  methylation. <https://www.nature.com/articles/s41587-019-0293-x>
- **DeepRepeat** — turns signal into images, CNN for quantification; no clean
  per-read count. <https://link.springer.com/article/10.1186/s13059-022-02670-6>
- **NanoSatellite** — earlier raw-squiggle DTW approach.
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6857246/>

### Basecalled-read (the current mainstream / SOTA)
- **STRkit** (2025, *Genome Research*) — read-level STR genotyping that also uses
  nearby SNVs; best on PacBio HiFi and short/intermediate alleles, but collapses
  on very large alleles. <https://genome.cshlp.org/content/36/3/578>
- **TRGT** — very strong on PacBio HiFi; reports methylation + mosaicism;
  PacBio-only. <https://www.nature.com/articles/s41587-023-02057-3>
- **LongTR**, **ATaRVa** — most robust on the independent Nanopore benchmark,
  including large alleles.
- **vamos**, **STRdust**, **Medaka Tandem** — competitive mid-tier / weaker.
- **Straglr** — whole-genome TR expansion discovery; slow/heavy.
  <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8361843/>

### Clinical / targeted workflows
- **HMMSTR** — profile-HMM copy-number caller, paired with multiplexed nCATS
  panels. <https://www.medrxiv.org/content/10.1101/2024.05.01.24306681v1.full>
- **RepeatHMM** — older HMM + GMM caller, ships HTT/FMR1/ATXN models.
  <https://github.com/WGLab/RepeatHMM>
- **NASTRA** — repeat-structure-aware forensic STR caller.
  <https://academic.oup.com/bib/article/25/6/bbae472/7774877>
- **MASTR-seq** (2026, *Cell Reports Methods*) — nanopore tract length +
  methylation on the same single molecule; *this is the source of our MASTR
  confirmation cohort*.
  <https://www.cell.com/cell-reports-methods/fulltext/S2667-2375(26)00041-X>

### Algorithmic family terms
DTW (speed-tolerant signal alignment, WarpSTR/NanoSatellite); HMM (STRique,
HMMSTR, RepeatHMM); GMM (turning many per-read counts into two alleles).

## 3. Anchor benchmarks & reviews (cite these)

- **Comprehensive Nanopore TR genotyping benchmark** (2026) — 7 basecalled-read
  tools; LongTR & ATaRVa most robust; large alleles (>1000 bp) are the hard wall
  (LongTR 89.7% vs STRkit 24.4%); R10 improves accuracy; **somatic mosaicism
  impact is explicitly unassessed = open problem**; tuning matters for long /
  mosaic / homopolymer loci. <https://pmc.ncbi.nlm.nih.gov/articles/PMC13001349/>
  (preprint <https://www.biorxiv.org/content/10.64898/2026.02.28.708646v1.full>)
- **RawBench** (Oct 2025, ETH/SAFARI) — first framework for raw-signal analysis;
  formalizes the pipeline as reference-encoding → **segmentation (= boundary
  detection, "a critical bottleneck")** → representation-matching; **Campolina**
  is a CNN that learns segmentation points (closest prior art to a learned
  boundary detector). <https://arxiv.org/pdf/2510.03629>
- **Nature Genetics review** (2026), "Toward the clinical application of long-read
  sequencing in repeat-expansion disorders" — the authoritative current clinical
  overview (somatic instability, allele-specific methylation).
  <https://www.nature.com/articles/s41588-026-02694-9>
- **ONT clinical diagnostics challenges** — names the unsolved problems and the
  need for standardized confidence/reporting.
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11942491/>

## 4. The open frontier (where meaningful questions live)

1. **Large / expanded alleles are still the hard wall.** Accuracy drops sharply
   for big expansions — *exactly this thesis's target*.
2. **Somatic mosaicism** — repeats differ cell-to-cell (large in HD neurons; the
   subject of the Cattaneo CAGinSTEM paper). Tools' handling is largely
   unassessed.
3. **Methylation + length together** — TRGT, MASTR-seq co-measure them per
   molecule; a growing direction.
4. **Signal vs basecalled** — R10.4.1 basecalling is good enough that many left
   raw signal; the live debate is *where raw signal still earns its keep* (our
   argument: the hardest expanded / interrupted cases).
5. **CAG interruptions** — pure vs interrupted CAG changes both the count and the
   pathology (Cattaneo 2025, Cell Reports, DOI 10.1016/j.celrep.2025.116685).
6. **Calibrated uncertainty / abstention is essentially absent** in signal-level
   STR calling — our niche, and the clinical reviews say it is needed.

## 5. Where this thesis sits

- Competes in the **signal-level regime** (comparators WarpSTR/STRique/DeepRepeat
  are the right peers). Justify the niche: raw signal is the system of record for
  the hardest repeats, where basecalling still drifts.
- Defensible **novelty is the narrow combination**: competitor-independent
  boundaries + unordered sample-level weak supervision + latent per-read
  assignment + calibrated uncertainty & abstention + nested sample-disjoint
  evaluation. Not "first neural / raw-signal STR caller" (prior art is explicit).
- Honest current result: independent duration MAE **1.638** (vs WarpSTR 0.722);
  neural residual and length-dependent ruler are **negative results**; the
  bottleneck is **expanded-allele data coverage**, confirmed experimentally.

## 6. Adjacent cutting-edge (one line each)
- **NanoSimFormer** (2026) — transformer signal *simulator* that reduces STR/
  homopolymer false positives; could generate training data for a data-starved
  model. <https://academic.oup.com/bioinformatics/article/42/6/btag402/8709229>
- **RNA tandem-repeat quantification by nanopore sensing** (2026, Nat Commun) —
  direct single-molecule sensing of DM1/DM2/CCHS repeats.
  <https://www.nature.com/articles/s41467-026-72819-5>

## 7. Reading order
1. Nature Genetics 2026 review (clinical framing).
2. The 2026 Nanopore benchmark (what's SOTA, what's hard).
3. RawBench (raw-signal pipeline + learned segmentation).
4. WarpSTR + STRique papers (your closest comparators' mechanics).
5. DeepRepeat (for the Fig. 4 A/D comparison format your supervisor asked for).
