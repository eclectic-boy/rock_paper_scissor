play:
	python game/main.py

check_all_code:
	pre-commit run -a

test:
	python -m unittest
