SHELL := /bin/bash

RUNNER := ont-str-runner
SCRIPTS := $(RUNNER)/scripts

SAMPLE ?= ND30626
REFERENCE_FASTA ?=
DATA_ROOT ?= $(RUNNER)/data
REPEAT_NAME ?= htt
COORD ?= chr4:3074876-3074933
MOTIF ?= CAG
MIN_REPEAT ?= 3
RUN_STRIQUE ?= 0
DRY_RUN ?= 0

define run
	@if [ "$(DRY_RUN)" -eq 1 ]; then \
		echo "+ $(1)"; \
	else \
		$(1); \
	fi
endef

.PHONY: all help warpstr-config warpstr deeprepeat strique run-sample batch dry-run batch-dry-run

all: run-sample

help:
	@echo "Targets:"
	@echo "  run-sample     Run WarpSTR, DeepRepeat, STRique for one sample"
	@echo "  batch          Run all HTT samples via run_all_htt_samples.sh"
	@echo "  dry-run        Print commands for run-sample without executing"
	@echo "  batch-dry-run  Print commands for batch without executing"
	@echo "  warpstr-config Generate WarpSTR config for SAMPLE"
	@echo "  warpstr        Run WarpSTR for SAMPLE"
	@echo "  deeprepeat     Run DeepRepeat for SAMPLE"
	@echo "  strique        Run STRique for SAMPLE"
	@echo ""
	@echo "Vars: SAMPLE, REFERENCE_FASTA, DATA_ROOT, REPEAT_NAME, COORD, MOTIF, MIN_REPEAT, RUN_STRIQUE, DRY_RUN"

warpstr-config:
	$(call run,bash "$(SCRIPTS)/make_warpstr_config.sh" "$(SAMPLE)" "$(REFERENCE_FASTA)" "$(DATA_ROOT)")

warpstr:
	$(call run,REFERENCE_FASTA="$(REFERENCE_FASTA)" DATA_ROOT="$(DATA_ROOT)" bash "$(SCRIPTS)/run_warpstr.sh" "$(SAMPLE)")

deeprepeat:
	$(call run,DATA_ROOT="$(DATA_ROOT)" bash "$(SCRIPTS)/run_deeprepeat.sh" "$(SAMPLE)" "$(REPEAT_NAME)" "$(COORD)" "$(MOTIF)" "$(MIN_REPEAT)")

strique:
	$(call run,DATA_ROOT="$(DATA_ROOT)" bash "$(SCRIPTS)/run_strique.sh" "$(SAMPLE)")

run-sample: warpstr deeprepeat strique

batch:
	$(call run,RUN_STRIQUE="$(RUN_STRIQUE)" DATA_ROOT="$(DATA_ROOT)" REFERENCE_FASTA="$(REFERENCE_FASTA)" bash "$(SCRIPTS)/run_all_htt_samples.sh")

dry-run:
	@$(MAKE) run-sample DRY_RUN=1 SAMPLE="$(SAMPLE)" REFERENCE_FASTA="$(REFERENCE_FASTA)" DATA_ROOT="$(DATA_ROOT)" \
		REPEAT_NAME="$(REPEAT_NAME)" COORD="$(COORD)" MOTIF="$(MOTIF)" MIN_REPEAT="$(MIN_REPEAT)"

batch-dry-run:
	@$(MAKE) batch DRY_RUN=1 RUN_STRIQUE="$(RUN_STRIQUE)" DATA_ROOT="$(DATA_ROOT)" REFERENCE_FASTA="$(REFERENCE_FASTA)"
