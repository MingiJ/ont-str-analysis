# Project Glossary — HTT CAG Nanopore STR Caller

Plain-English definitions of every major concept in this project. Each entry:
**what it is** → **why it matters here** (with a concrete example from our data
where useful). Keep this open while you work. Pair with
`docs/DECISION_REVIEW_GUIDE.md` (how to review) and `docs/DEFENSE_PREP.md`.

---

## 1. The biology (what we're measuring)

**DNA bases (nucleotides)** — the letters of DNA: A, C, G, T. `CAG` is three of
them in a row. *Not* proteins.

**CAG repeat** — a stretch where the pattern `CAG CAG CAG…` repeats many times,
inside the HTT gene. We count *how many* times it repeats.

**Codon / polyglutamine** — each `CAG` codon codes for one glutamine amino acid.
A long CAG repeat → an abnormally long "polyglutamine tail" in the huntingtin
protein → toxic. So "more CAG repeats" literally means "longer toxic tail."

**HTT gene** — the gene on chromosome 4 that carries this CAG repeat. Its exact
repeat location in our reference is `chr4:3074876–3074933`.

**Huntington's disease (HD)** — the disease caused by an expanded HTT CAG repeat.
Normal is roughly <27 repeats; ~36+ causes disease.

**Allele** — one of your two copies of a gene (one per chromosome). You have two
HTT alleles, so two CAG counts.

**Diploid** — having two copies of each chromosome (one from each parent). Hence
two alleles.

**Genotype** — the pair of allele values, e.g. `17/57`.

**Unordered genotype** — `17/57` and `57/17` are the *same* genotype; we don't
know which physical chromosome is which. This is why our method is trained on an
*unordered* pair.

**Autosomal dominant** — one bad copy is enough to cause disease. That's why HD
patients show up as one short + one long allele (e.g. `17/57`), while healthy
people are two short alleles (e.g. `17/18`).

**Expansion / expanded allele** — the long, disease-causing allele (e.g. the 57
or 72). These are the hard, clinically important cases and where our method
struggles most.

**Short / long allele** — the two alleles of a sample, by size. "Short" ≈ normal
(~17–21 here); "long" ≈ the possibly-expanded one (39–72 here).

**Sanger sequencing / capillary sizing** — the gold-standard, highly accurate
lab method for measuring repeat length. Slow, low-throughput, trusted. **Our
ground-truth counts come from this** (the Monteys 2017 table). Everything we
report error *against* is the Sanger truth.

**Ground truth / truth label** — the trusted correct answer (the Sanger counts).
We only trust it at the *sample* level (one `short/long` pair per person), never
per individual read.

---

## 2. Nanopore sequencing and the raw signal

**Oxford Nanopore sequencing (ONT)** — a sequencing technology where a single DNA
strand is pulled through a tiny pore while an electrical current is measured
thousands of times per second (4000 Hz in our data).

**Pore / ionic current** — the DNA partially blocks ions flowing through the
pore, changing the measured current. Different bases block it differently.

**k-mer** — the pore is long enough that **several bases (~5–6, a "k-mer") sit in
the sensing region at once**, so each current reading reflects a *window* of
bases, not a single base. (This is why the signal is subtle for repeats.)

**Raw signal / squiggle** — the raw sequence of current measurements for a read.
A wiggly list of numbers. This is the "system of record" — the real data before
any interpretation.

**FAST5** — the file format storing the raw signal (and sometimes analysis
results) for nanopore reads. (POD5 is the newer format; our MASTR data used it.)

**Basecalling / basecaller** — the step that translates the raw signal into DNA
letters (A/C/G/T). Tools: **Guppy** (older), **Dorado** (current). Basecallers
make more errors on long repeats — which is why working from *raw signal* can
beat working from the basecalled letters.

**Move table** — ⚠ *the one you keep struggling with.* As the basecaller walks
along the raw signal emitting letters, it records **how many signal samples it
consumed for each base** — a per-base tally. That tally is the move table. It is
the bridge that maps **base index → raw-signal-sample index**. Without it you
can't say which chunk of signal produced which base. We read it from the FAST5
to find where in the signal the CAG repeat sits.

**Duration / dwell time** — how many raw signal samples a region occupies =
(repeat_end − repeat_start) in samples. Longer DNA → more time in the pore →
more samples. **This is the core feature of our best method:** duration →
CAG count.

**Samples per CAG / "the ruler"** — how many raw samples correspond to one CAG
unit (~33 in our data). Duration ÷ ruler = CAG count. The ruler isn't perfectly
constant (it varies ~29–38 and drifts by read/allele), which is the main source
of our error.

**Normalization (median/MAD)** — re-centering each read's signal so reads are
comparable (subtract the median, divide by the median-absolute-deviation). That's
why normalized values hover around 0 in "standard-deviation" units.

**R9.4.1 / R10.4.1 chemistry** — generations of nanopore pore chemistry. Our
development data and the external cohorts are R9.4.1; it matters because models
and basecallers are chemistry-specific.

---

## 3. Alignment and coordinates (bioinformatics plumbing)

**Reference genome** — the agreed-upon standard human DNA sequence (~3 billion
letters). Like a giant known book. Chromosome 4 is one chapter.

**Alignment** — finding *where* a read's letters match in the reference book.
This is how a read's bases tell you "this is chr4 at position X." Tool: minimap2.

**BAM file** — ⚠ *the other one you keep struggling with.* A BAM is a compressed
table of **reads that have been aligned to the reference**. One row per read,
and each row stores: the read's bases, its quality scores, **where it aligned**
(chromosome + position), the **CIGAR** string (see below), the **MAPQ** (see
below), the strand, and flags. (SAM is the same thing in plain text; BAM is the
compressed binary version; `.bai` is its index for fast lookup.) Think of it as:
*"for every read, here is where it landed in the genome and how."* We use it to
find which reads overlap the HTT locus and to walk from reference coordinates to
the read's own bases. Inspect it with **samtools** (`samtools view file.bam
chr4:3074876-3074933`).

**CIGAR** — a compact code in each BAM row describing how the read aligns:
matches, insertions, deletions, soft-clips. We follow the CIGAR to map a
reference position to the corresponding position in the read's bases.

**MAPQ** — "mapping quality": how confident the aligner is that the read is in the
*right* place (not a similar-looking spot elsewhere). 60 = very confident; low
(e.g. 2–7) = possibly mis-mapped. We discard low-MAPQ reads because their
coordinates can't be trusted.

**Strand (+/−)** — which direction the read aligned (forward or reverse
complement). Just a direction flag.

**Soft clipping** — parts of a read that didn't align (e.g. messy ends), reported
in the CIGAR. Lots of soft-clipping is a red flag for a bad/ambiguous read.

**The three coordinate systems (and why we chain them)**:
1. **Reference coordinates** — position in the standard genome (same for
   everyone; knows nothing about this read's signal).
2. **Query / read coordinates** — position within *this read's* bases.
3. **Signal coordinates** — index into *this read's* raw signal samples.
   We map **reference → read (via CIGAR) → signal (via move table)** because the
   read's own bases are the only thing that lives in both the genome world and
   the signal world. You can't skip the middle.

**BED file** — a tiny text file giving genome regions as `chrom start end`. Ours
pin the HTT locus (`chr4 3074876 3074933`).

**Locus** — a specific location in the genome. Our locus is the HTT CAG box.

---

## 4. The existing tools (our comparators)

**WarpSTR** — raw-signal caller using a DTW-like alignment to a finite-state
repeat model + sample-level GMM genotyping. Strongest comparator (MAE 0.722).

**STRique** — raw-signal caller: aligns repeat boundaries, counts with an HMM.
(MAE 1.667.)

**DeepRepeat** — turns signal into images and uses a CNN; reports allele
allocations, not clean per-read counts. (Allocation-peak MAE 1.556.)

**DTW (Dynamic Time Warping)** — an algorithm that aligns two signals that may
run at different speeds; accurate but slow. Used by WarpSTR/NanoSatellite.

**HMM (Hidden Markov Model)** — a probabilistic state model; STRique uses one to
count repeats.

**GMM (Gaussian Mixture Model)** — clusters values into Gaussian "humps"; used to
turn many per-read counts into two allele calls.

---

## 5. Machine learning and evaluation (what makes a result trustworthy)

**Train / validation / test** — *train* = the model learns; *validation* = you
tune choices (which model, how many rounds) and keep the best; *test* = the
final, untouched exam you look at once. Tuning on the test set is cheating — the
score stops being honest.

**MAE (mean absolute error)** — average size of the miss, ignoring direction. Our
headline metric, in CAG repeats. `1.638` = average allele miss over the nine
held-out samples.

**LOSO (leave-one-sample-out)** — hold out an *entire person*, train on the other
eight, predict the held-out one; repeat for all nine. The correct split here,
because reads from one person are correlated (same genotype, prep, flow cell) —
a random *read* split would leak and inflate the score.

**Nested LOSO** — when you also need to *choose* something (a threshold, a model,
a feature shape), you choose it using an inner LOSO on the training samples only,
never the held-out one. Prevents selection leakage.

**Data leakage** — when information from the test answer sneaks into training or
model choice, making the score look better than reality. Examples here: using
WarpSTR's boundaries as inputs; or picking a feature shape after seeing all nine
samples' results.

**Overfitting / hindsight / "fixed-vs-nested" trap** — a number that looks great
because a choice was made *after* peeking (e.g. fixed ACF 1.414, fixed isotonic
1.53) but collapses when chosen honestly (nested ACF 1.725, nested ruler 1.69).
Spotting this is the core review skill.

**Weak supervision** — training with a weaker label than you'd like. Here: only
the *sample-level* unordered pair `{17,57}`, never a per-read label.

**Latent variable / per-read assignment** — the model treats "which allele did
this read come from?" as an unknown it infers, rather than being told.

**Calibration** — converting a raw measurement into the target unit using a fit
(e.g. duration → CAG via `count = a + b·duration`), fitted on training samples.

**Uncertainty / heteroscedastic** — the model also reports *how unsure* it is, and
the uncertainty can differ per read ("heteroscedastic" = non-constant variance).

**Abstention / coverage** — the caller may refuse to answer ("abstain") when
evidence is weak. *Coverage* = fraction of samples it did answer. You must report
coverage *and* error together — low error achieved by abstaining on the hard
cases is not a win.

**Negative result** — a rigorously-evaluated finding that something does *not*
work (e.g. the neural residual, the length-dependent ruler). Done under a sound
protocol, it's a genuine contribution, not a failure.

**Autocorrelation (ACF)** — measures how periodic a signal is (slide it against
itself). We tried it as a per-read "speedometer" to fix the ruler; it didn't beat
the baseline once chosen honestly. See the "fixed-vs-nested trap."

**Bimodal / bimodality** — a distribution with two humps. For a `17/57` sample,
the per-read estimates should form two humps (one near 17, one near 57). Your
supervisor's early check was whether the per-read estimates are bimodal.

---

## 6. This project's specific results (know these cold)

| Thing | Value | Meaning |
|---|---|---|
| Independent duration baseline | 1.638 | **Defensible headline.** Pure physics on independently-mapped boundaries; no competitor input; no uncertainty layer. |
| WarpSTR | 0.722 | Strongest comparator. The bar to clear. |
| DeepRepeat (allocation peaks) | 1.556 | Comparator; no clean per-read count. |
| STRique | 1.667 | Comparator. |
| Engineered MLP | 0.556 | Lowest but **tainted** — uses WarpSTR-derived boundaries, so NOT an independent win. |
| Weak-supervised RNN | 5.775 | Negative result; neural residual hurts. |
| Length-dependent ruler (nested) | 1.69 | Negative result; data coverage, not ruler shape, is the limit. |

**The nine samples** — GM04723 (72/17), ND30015 (41/20), ND30016 (41/21),
ND30047 (41/18), ND30422 (40/18), ND30626 (41/21), ND31551 (39/18),
ND33392 (57/17), ND33947 (40/18). Only two carry real expansions (72, 57).

**REL3** — an unlabelled public whole-genome nanopore sample (NA12878). Used for
qualitative/independence checks only; no accuracy number, because there's no
trusted genotype.

**External confirmation (Coriell, MASTR)** — extra cohorts of different chemistry
used to test whether the method transfers. Both frozen; MASTR failed its
pre-declared accuracy gate. They're transfer tests, not clinical validation.
