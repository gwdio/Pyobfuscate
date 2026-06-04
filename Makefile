.PHONY: help install serve cli verify test build build-lambda build-package deploy plan tf-init tf-validate clean

PYTHON   := python3
UVICORN  := uvicorn
TF       := terraform
TF_DIR   := infra

# ── Help ─────────────────────────────────────────────────────────────────────

help:
	@echo "Dev"
	@echo "  install        pip install -r requirements.txt"
	@echo "  serve          uvicorn app:app --reload"
	@echo "  cli            run obfuscate.py interactively"
	@echo "  verify         diff IO/input.py vs IO/output.py runtime output"
	@echo "  test           run pytest test suite"
	@echo ""
	@echo "Build"
	@echo "  build          build-lambda + build-package"
	@echo "  build-lambda   package dist/lambda.zip for AWS Lambda"
	@echo "  build-package  generate frontend/package.json for Pyodide"
	@echo ""
	@echo "Deploy"
	@echo "  deploy         build then terraform apply"
	@echo "  plan           build then terraform plan"
	@echo "  tf-init        terraform init"
	@echo "  tf-validate    terraform validate"
	@echo ""
	@echo "Misc"
	@echo "  clean          remove build artifacts"

# ── Dev ──────────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt

serve:
	$(UVICORN) app:app --reload

cli:
	$(PYTHON) obfuscate.py

verify:
	$(PYTHON) IO/input.py > /tmp/original.out
	$(PYTHON) IO/output.py > /tmp/obfuscated.out
	diff /tmp/original.out /tmp/obfuscated.out && echo "OK: outputs match"

test:
	pytest

# ── Build ────────────────────────────────────────────────────────────────────

build: build-lambda build-package

build-lambda:
	bash scripts/build_lambda.sh

build-package:
	$(PYTHON) scripts/build_package_json.py

# ── Deploy ───────────────────────────────────────────────────────────────────

deploy: test build
	cd $(TF_DIR) && $(TF) apply

plan: build
	cd $(TF_DIR) && $(TF) plan

tf-init:
	cd $(TF_DIR) && $(TF) init

tf-validate:
	cd $(TF_DIR) && $(TF) validate

# ── Misc ─────────────────────────────────────────────────────────────────────

clean:
	rm -f dist/lambda.zip /tmp/original.out /tmp/obfuscated.out
