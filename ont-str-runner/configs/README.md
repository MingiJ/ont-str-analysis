# Configs

This folder holds configuration files for the runners.

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
