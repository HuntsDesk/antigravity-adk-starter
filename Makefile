AGENTS = access_triage access_triage_panel access_triage_mcp access_triage_guarded

# Copy the root .env into every agent folder (adk web reads .env per agent).
env:
	@test -f .env || (echo "Create .env first: cp .env.example .env" && exit 1)
	@for a in $(AGENTS); do cp .env $$a/.env; done
	@echo "Copied .env into: $(AGENTS)"

test:
	python -m pytest -q

answer-key:
	python run_answer_key.py access_triage
