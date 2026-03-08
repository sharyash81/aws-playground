.PHONY: help init plan deploy destroy outputs \
	local-setup local-clean local-gen local-load local-run local-all \
	local-benchmark \
	build-tools lambda-gen athena-create athena-smoke pipeline

SHELL := /bin/bash
TF_DIR := terraform
SCRIPTS := scripts
VENV ?= .venv
REGION ?= us-east-1
SF ?= 1
CHUNK ?= 0
TOTAL_CHUNKS ?= 1
S3_PREFIX ?= tpch-data
GEN_TOOL ?= tpchgen-rs
RESULTS_PREFIX ?= athena-results
RESULT_TAG ?= $(GEN_TOOL)
DATA_DIR := data/sf$(SF)_$(RESULT_TAG)
DB_FILE := tpch_sf$(SF)_$(RESULT_TAG).duckdb
RESULTS_DIR := results/sf$(SF)_$(RESULT_TAG)

BUCKET := $(shell terraform -chdir=$(TF_DIR) output -raw s3_bucket_name 2>/dev/null)
LAMBDA_GEN := $(shell terraform -chdir=$(TF_DIR) output -raw lambda_function_name 2>/dev/null)
ATHENA_DB := $(shell terraform -chdir=$(TF_DIR) output -raw athena_database_name 2>/dev/null)
ATHENA_WG := $(shell terraform -chdir=$(TF_DIR) output -raw athena_workgroup_name 2>/dev/null)

help:
	@echo "TPC-H playground commands"
	@echo "  make local-setup"
	@echo "  make build-tools"
	@echo "  make local-all SF=1 GEN_TOOL=tpchgen-rs"
	@echo "  make local-benchmark SF=1"
	@echo "  make deploy"
	@echo "  make pipeline SF=1 CHUNK=0 TOTAL_CHUNKS=1 GEN_TOOL=tpchgen-rs"

init:
	terraform -chdir=$(TF_DIR) init

plan:
	terraform -chdir=$(TF_DIR) plan

deploy:
	terraform -chdir=$(TF_DIR) apply -auto-approve

destroy:
	terraform -chdir=$(TF_DIR) destroy -auto-approve

outputs:
	terraform -chdir=$(TF_DIR) output

local-setup:
	python3 -m venv $(VENV)
	source $(VENV)/bin/activate && pip install --upgrade pip
	source $(VENV)/bin/activate && pip install -r requirements.txt

build-tools:
	source $(VENV)/bin/activate && python3 $(SCRIPTS)/build_dbgen.py --tool both --prepare-lambda

local-clean:
	rm -rf data/sf* results/sf* results/benchmarks tpch_sf*.duckdb response.json payload.b64

local-gen:
	source $(VENV)/bin/activate && python3 $(SCRIPTS)/gen_tpch_data.py --tool $(GEN_TOOL) --sf $(SF) --out $(DATA_DIR)

local-load:
	source $(VENV)/bin/activate && python3 $(SCRIPTS)/load_duckdb.py --data $(DATA_DIR) --db $(DB_FILE)

local-run:
	source $(VENV)/bin/activate && python3 $(SCRIPTS)/run_queries.py --db $(DB_FILE) --queries queries/tpch.sql --out $(RESULTS_DIR)

local-all: local-gen local-load local-run

local-benchmark:
	source $(VENV)/bin/activate && python3 $(SCRIPTS)/benchmark_generators.py \
		--sf $(SF) \
		--out results/benchmarks/sf$(SF)_generator_benchmark.json

lambda-gen:
	@echo '{"scale_factor":"$(SF)","chunk":$(CHUNK),"total_chunks":$(TOTAL_CHUNKS),"s3_prefix":"$(S3_PREFIX)","tool":"$(GEN_TOOL)"}' | base64 > payload.b64
	aws lambda invoke \
		--function-name $(LAMBDA_GEN) \
		--payload file://payload.b64 \
		--region $(REGION) \
		response.json >/dev/null
	@jq -r '.body' response.json

athena-create:
	source $(VENV)/bin/activate && python3 $(SCRIPTS)/athena_runner.py create-tables \
		--region $(REGION) \
		--database $(ATHENA_DB) \
		--workgroup $(ATHENA_WG) \
		--s3-bucket $(BUCKET) \
		--results-prefix $(RESULTS_PREFIX) \
		--ddl-template queries/athena_ddl.sql \
		--s3-prefix $(S3_PREFIX) \
		--sf $(SF) \
		--chunk $(CHUNK)

athena-smoke:
	source $(VENV)/bin/activate && python3 $(SCRIPTS)/athena_runner.py run-query \
		--region $(REGION) \
		--database $(ATHENA_DB) \
		--workgroup $(ATHENA_WG) \
		--s3-bucket $(BUCKET) \
		--results-prefix $(RESULTS_PREFIX) \
		--sql "SELECT COUNT(*) AS total_rows FROM customer"

pipeline: lambda-gen athena-create athena-smoke
	@echo "Pipeline complete:"
	@echo "  s3://$(BUCKET)/$(S3_PREFIX)/sf$(SF)/chunk$(CHUNK)/"
