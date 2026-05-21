from scripts.workflow import contribute_back


def test_classify_paths_routes_categories():
    paths = [
        "presets/customer.seed.md",
        "catalogs/preset-catalog.yaml",
        "templates/jakarta/entity.java.j2",
        "patterns/D2/manifest.yaml",
        "scripts/dialect_mysql.py",
        "README.md",
    ]
    grouped = contribute_back.classify(paths)
    assert "presets/customer.seed.md" in grouped["catalog"]
    assert "catalogs/preset-catalog.yaml" in grouped["catalog"]
    assert "templates/jakarta/entity.java.j2" in grouped["template"]
    assert "patterns/D2/manifest.yaml" in grouped["pattern"]
    assert "scripts/dialect_mysql.py" in grouped["dialect"]
    assert "README.md" in grouped["other"]


def test_classify_empty_input():
    assert contribute_back.classify([]) == {
        "catalog": [], "template": [], "pattern": [], "dialect": [], "other": []
    }


def test_questions_for_returns_one_per_category():
    paths = ["presets/x.seed.md", "templates/jakarta/y.j2"]
    qs = contribute_back.questions_for(contribute_back.classify(paths))
    cats = {q["category"] for q in qs}
    assert cats == {"catalog", "template"}
