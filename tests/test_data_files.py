# tests/test_data_files.py
import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"


def _load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def test_folklore_shape():
    items = _load("dark_folklore.json")
    assert len(items) >= 15
    ids = [x["id"] for x in items]
    assert len(ids) == len(set(ids))  # unique ids
    for x in items:
        assert set(x) >= {"id", "title", "culture", "text"}
        assert x["text"].strip()


def test_myths_shape_and_cast():
    myths = _load("myths.json")
    assert len(myths) >= 20
    ids = [m["id"] for m in myths]
    assert len(ids) == len(set(ids))
    for m in myths:
        assert set(m) >= {"id", "title", "text", "cast"}
        assert 1 <= len(m["cast"]) <= 3


def test_every_art_constellation_has_a_myth():
    consts = _load("constellations.json")
    names = {c["name"] for c in consts}
    art = _load("myth_art.json")
    myths = _load("myths.json")
    cast_names = {n for m in myths for n in m["cast"]}
    # art keys must all be real constellations
    assert set(art) <= names
    # every art constellation must be castable
    assert set(art) <= cast_names, set(art) - cast_names
    # every cast name must be a real constellation (guards typos)
    assert cast_names <= names, cast_names - names


def test_mythology_json_removed():
    assert not (DATA / "mythology.json").exists()
