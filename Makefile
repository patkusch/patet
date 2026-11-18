.PHONY: help test live scan-examples commit

help:
	@echo "make test           run the unit tests"
	@echo "make live           run the live test (needs PostgREST on :3000, see live/README.md)"
	@echo "make scan-examples  scan the clean and leaky example folders"

test:
	PYTHONPATH=src:tests python3 -m unittest discover -s tests

live:
	python3 live/run.py

scan-examples:
	PYTHONPATH=src python3 -m patet scan examples/clean
	PYTHONPATH=src python3 -m patet scan examples/leaky || echo "leaky failed, as it should"

# Commit only when the tests pass. The exit code of the test run decides, nothing else.
commit: test
	git -c user.name=patkusch -c user.email=309124786+patkusch@users.noreply.github.com commit -qm "$(MSG)"
	git push -q
