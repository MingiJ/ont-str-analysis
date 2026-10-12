# Configs

This folder holds configuration files for the runners.

## Truth sample manifest
`truth_samples.tsv` lists the public SRA source archives used for the HTT CAG
benchmark. The strict thesis benchmark uses rows with `include_primary=1`.

`external_confirmation_samples.tsv` freezes the public external-confirmation
cohort before evaluation. It records Coriell truth, BioSample/SRA identity,
raw FAST5/SLOW5 accessions, object sizes, checksums, and the preferred
technical replicate. The current eligible samples are NA13509 (`15/70`) and
NA13512 (`16/44`) from `SRP349335`; NA13509's second run is reserved as a
technical-replicate robustness check.

The raw objects are intentionally not downloaded wholesale. Build a remote tar
member index with `src/algorithm/http_tar_members.py`, then stream only the
embedded pass FASTQ through
`ont-str-runner/scripts/prepare_external_confirmation.sh`. This preserves the
original FASTQ timestamp in the BAM so the small chronological multi-FAST5
batch containing each HTT read can be retrieved later.

## Independent MASTR-seq confirmation

`mastr_confirmation_acquisition.tsv` freezes four public HTT samples from
`SRP504233` before prediction. It records the SRA/GEO identities, barcode
mapping, ENA FASTQ checksums, the Zenodo POD5 checksum, and the exact Dorado
model. Genotype truth is deliberately isolated in
`mastr_confirmation_truth.tsv`, which must be opened only by the scoring step.

`mastr_runtime_versions.tsv` records the executable/model/library versions and
the chemistry audit read directly from `FAW16852.pod5`. Although the paper
also discusses R10.4.1 data, this HTT POD5 reports `FLO-MIN106`, `sqk-lsk109`,
and 4,000 Hz; it is therefore an independent targeted-library R9.4.1 cohort,
not a cross-chemistry cohort. The ENA/SRA FASTQ headers are archive-local
ordinals and cannot be joined to raw UUIDs. The frozen workflow consequently
uses a Dorado FAST barcode/locus pass to select UUIDs, followed by SUP
basecalling only for the bounded confirmatory subset.

The final sample join is sequence-audited: barcode10 maps to parental
`SRR35299134`, barcode09 to normal `SRR35299133`, barcode11 to expanded-56
`SRR35299132`, and barcode12 to expanded-72 `SRR35299131`. The archive audit
caught the initial barcode09/barcode10 reversal before SUP prediction or
truth access.

Download all primary truth-sample archives:
```bash
bash ../scripts/download_truth_samples.sh
```

Download only missing samples:
```bash
bash ../scripts/download_truth_samples.sh ND31551 ND33947
```

## WarpSTR configs
WarpSTR configs are generated automatically by:
```bash
REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
  bash ../scripts/make_warpstr_config.sh <SAMPLE> "$REFERENCE_FASTA"
```
The generated config is written to:
```
configs/warpstr_<SAMPLE>.yaml
```

You can also copy and edit `../templates/warpstr_template.yaml` if you need non-HTT loci or custom settings.

## STRique config
`strique_config.tsv` defines the STR locus and flanking sequences. The column order must be:
```
chr    begin    end    name    repeat    prefix    suffix
```
