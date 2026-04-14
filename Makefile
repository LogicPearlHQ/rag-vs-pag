.PHONY: install fetch index build demo test smoke clean

install:
	uv sync --extra dev

fetch:
	uv run python -m corpus.fetch

index:
	uv run python -m rag.index

build:
	bash pearl/build.sh

demo:
	uv run python compare.py --repeat 5

smoke:
	uv run python compare.py --only 01_classified_memo --repeat 1

test:
	uv run pytest -q

clean:
	rm -rf corpus/raw pearl/artifact rag/index
