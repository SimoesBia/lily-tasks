import pytest

pytest.importorskip("pydantic.fields")  # exige o pydantic REAL (o schema depende dele)

from lily import schemas as s  # noqa: E402
from lily.tools import to_gemini_schema  # noqa: E402
from tests.helpers import make_runtime  # noqa: E402


def test_gemini_schema_is_flat_and_complete():
    sch = to_gemini_schema(s.CreateTaskArgs)
    assert sch["type"] == "object" and sch["required"] == ["title"]
    assert sch["properties"]["priority"]["enum"] == ["baixa", "media", "alta"]
    assert sch["properties"]["due"]["type"] == "string"  # Optional[str] virou string simples
    blob = str(sch)
    assert "anyOf" not in blob and "$ref" not in blob  # estrutura achatada, como o Gemini espera
    assert "default" not in blob  # metadados do Pydantic não vazam para a declaração


def test_every_tool_has_a_valid_declaration():
    rt, _ = make_runtime()
    decls = rt.registry.declarations()
    assert len(decls) == len(rt.registry.names) >= 11
    for d in decls:
        assert d["name"] and d["description"] and d["parameters"]["type"] == "object"


def test_strict_models_reject_unknown_fields_and_bad_enums():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        s.CreateTaskArgs.model_validate({"title": "x", "extra": 1})
    with pytest.raises(ValidationError):
        s.DraftEmailArgs.model_validate({"purpose": "spam"})
