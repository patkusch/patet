test:
	PYTHONPATH=src:tests python3 -m unittest discover -s tests

# Commit only when the tests pass. The exit code of the test run decides, nothing else.
commit: test
	git -c user.name=patkusch -c user.email=309124786+patkusch@users.noreply.github.com commit -qm "$(MSG)"
	git push -q
