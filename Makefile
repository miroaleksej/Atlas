.PHONY: collect research-triage targeted first-experiment real-experiment frontier-scan science-atlas self-repair replay-prepare replay-batches replay-aggregate full qualify release-controls seal-audit audit-read-only clean

PYENV = PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

collect:
	$(PYENV) pytest --collect-only -q -p no:cacheprovider

research-triage:
	$(PYENV) python -m evaluation.research_triage_qualification
	$(PYENV) pytest -q -p no:cacheprovider tests/test_research_triage.py

targeted:
	$(PYENV) pytest -q -p no:cacheprovider tests/test_science_atlas_core.py tests/test_domain_plugin_architecture.py tests/test_adaptive_axis_discovery.py tests/test_electronic_state_space_current.py

first-experiment:
	$(PYENV) python -m evaluation.first_atlas_native_experiment > /tmp/FIRST_POST_CLEAN_ATLAS_EXPERIMENT_REPLAY.json

real-experiment:
	$(PYENV) python -m evaluation.axis_modeling_realdata_qualification --blind-current > reports/BLIND_REAL_PHYSICS_EXPERIMENT_CURRENT.json

frontier-scan:
	$(PYENV) python -c 'from source.lawspace.scientific_exploitation import write_current_state; write_current_state(".", ai_extension_verified=True)'
	$(PYENV) python -m evaluation.lawspace_qualification --refresh-measurement-depth-current --output reports/ATLAS_FRONTIER_SCAN_CURRENT.json

science-atlas:
	$(PYENV) python -m evaluation.science_atlas_core_qualification > /tmp/SCIENCE_ATLAS_PRODUCTION_QUALIFICATION_CURRENT.json

self-repair:
	$(PYENV) python -c 'import json; from source.lawspace.api import LawSpaceAPI; print(json.dumps(LawSpaceAPI(".").run_phi_runtime_self_repair_cycle(), ensure_ascii=False, indent=2, sort_keys=True))' > /tmp/phi_runtime_self_repair_current.json
	mv /tmp/phi_runtime_self_repair_current.json reports/RUNTIME_SELF_REPAIR_CURRENT.json

replay-prepare:
	$(PYENV) python -m evaluation.full_replay_qualification --prepare > /tmp/phi_full_replay_prepare.json

replay-batches: replay-prepare
	@count=$$(python -m evaluation.full_replay_qualification --print-batch-count | python -c 'import json,sys; print(json.load(sys.stdin)["batch_count"])'); \
	i=0; while [ $$i -lt $$count ]; do \
		echo "full replay batch $$i/$$((count-1))"; \
		$(PYENV) python -m evaluation.full_replay_qualification --batch $$i > /tmp/phi_full_replay_batch_$$i.json || exit $$?; \
		i=$$((i+1)); \
	done

replay-aggregate:
	$(PYENV) python -m evaluation.full_replay_qualification --aggregate > /tmp/phi_full_replay_current.json
	cp /tmp/phi_full_replay_current.json reports/FULL_HEAVY_REPLAY_CURRENT.json

full: replay-batches replay-aggregate

qualify: real-experiment frontier-scan
	$(PYENV) python -m evaluation.unified_release_qualification

release-controls:
	$(PYENV) python -m evaluation.build_release_controls

seal-audit:
	$(PYENV) python -m evaluation.seal_audit

# Strict audit: no bytecode, reports or mutable state may be created in the sealed tree.
audit-read-only:
	PYTHONDONTWRITEBYTECODE=1 $(PYENV) python -m evaluation.read_only_audit

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	find reports -maxdepth 1 -type f -name '*.tmp' -delete
	rm -f reports/FIRST_POST_CLEAN_ATLAS_EXPERIMENT_CURRENT.json
	rm -f reports/THEORY_COMPILER_QUALIFICATION_CURRENT.json reports/ATOMIC_OPERATOR_PROBE_CYCLE_CURRENT.json reports/ATOMIC_VARIABLE_PARTICLE_SELF_CONSISTENT_CYCLE_CURRENT.json
	rm -f reports/FULL_HEAVY_REPLAY_CURRENT.json
	rm -rf reports/runtime
