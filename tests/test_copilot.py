"""Tests of the copilot's guardrails, all offline.

The interesting tests here are the negative ones: the module has to *reject* a draft
that invents a quantity or promises compliance, because that is the risk the master
document names (alucinaciones del LLM en documentos o propuestas).
"""

import pytest
from pydantic import BaseModel

from scraper.copilot import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    OutreachDraft,
    Template,
    approve,
    assemble_message,
    build_prompt,
    draft_outreach,
    facts_from_prospect,
    litellm_completer,
    load_template,
    quantities_in,
    reject,
    sensitive_terms_in,
    submission_to_dict,
    verify_draft,
)
from scraper.contract import Prospect

TEMPLATE = Template(
    name="oaas-v1",
    text=(
        "{subject}\n\n"
        "{greeting}\n\n"
        "{opening}\n\n"
        "Le proponemos el modelo de ozonoterapia en comodato, con un minimo de consumo "
        "de insumos y soporte tecnico local.\n\n"
        "{talking_points}\n\n"
        "Quedo a disposicion para coordinar una visita tecnica.\n\n"
        "[FIRMA DEL DUEÑO]\n"
    ),
)

PARRAFO_DEL_DUEÑO = (
    "Le proponemos el modelo de ozonoterapia en comodato, con un minimo de consumo "
    "de insumos y soporte tecnico local."
)


@pytest.fixture(autouse=True)
def clean_learned_format():
    """`_WORKING_ATTEMPT` is memoised per process: a test must not inherit it."""
    from scraper import copilot

    copilot._WORKING_ATTEMPT.clear()
    yield
    copilot._WORKING_ATTEMPT.clear()


def prospect(**overrides) -> Prospect:
    """The shape of a real prospect, with capacity on record."""
    base = dict(
        id="00024663",
        ipress_code="00024663",
        name="CENTRO MEDICO ESPECIALIZADO SAN FELIPE",
        institution="PRIVADO",
        category="I-3",
        classification="CENTROS DE SALUD CON CAMAS DE INTERNAMIENTO",
        establishment_type="ESTABLECIMIENTO DE SALUD CON INTERNAMIENTO",
        location={
            "department": "LIMA",
            "province": "LIMA",
            "district": "LURIGANCHO",
            "ubigeo": "150118",
        },
        contact={"phone": "987243367", "phone_valid": True, "address": "JR. PUNO 182", "schedule": ""},
        capacity={"doctors_total": 27, "consulting_rooms": 7, "period": "2026-08"},
        ozone_therapy={},
        score={"total": 100, "level": "high", "components": {}, "measured_weight": 100},
        tags=["target-profile", "priority-high"],
    )
    base.update(overrides)
    return Prospect(**base)


def clean_draft(**overrides) -> OutreachDraft:
    base = dict(
        subject="Unidad de ozonoterapia para su centro medico",
        greeting="Estimado director medico:",
        opening=(
            "Le escribo porque su establecimiento es un centros de salud con camas de "
            "internamiento en el distrito de Lurigancho."
        ),
        talking_points=[
            "Registran 27 medicos, una base amplia para una unidad de dolor.",
            "Estan en el distrito de Lurigancho, dentro de nuestra cobertura de Lima.",
        ],
    )
    base.update(overrides)
    return OutreachDraft(**base)


def fake_completer(*, model, system, user, schema: type[BaseModel]):
    """A model that always returns the draft we planted, never a real network call."""
    return fake_completer.planted


# --- facts ------------------------------------------------------------------


def test_facts_leave_an_unknown_headcount_unknown():
    """A clinic with no capacity record is not a clinic with zero doctors.

    If the facts said 0, the model would write "0 medicos" and that is a fabricated
    claim about a real clinic.
    """
    sin_dato = facts_from_prospect(prospect(capacity={"doctors_total": 0, "period": None}))
    assert sin_dato.doctors_total is None
    assert "sin dato en el registro" in sin_dato.render()
    assert "0 medicos" not in sin_dato.render()


def test_facts_render_the_real_data():
    facts = facts_from_prospect(prospect())
    rendered = facts.render()
    assert "CENTRO MEDICO ESPECIALIZADO SAN FELIPE" in rendered
    assert "LURIGANCHO" in rendered
    assert "medicos registrados: 27" in rendered


# --- un prospecto del segmento no tiene campos del padrón --------------------- #
#
# Medido: la prueba en seco de los borradores del segmento explotó con
# `AttributeError: 'NoneType' object has no attribute 'level'`, porque el copiloto leía el
# puntaje del padrón sin preguntar si existía.


def place_prospect(**overrides):
    from scraper.contract import Prospect

    base = dict(
        id="places:1",
        origin="places",
        name="FISIOTERAPIA Y VIDA",
        location={"department": "LIMA", "district": "LIMA"},
        contact={"phone": "989 361 072", "phone_valid": True},
        google={
            "cid": "1",
            "query": "fisioterapia Lima Lima",
            "category": "Clínica de fisioterapia",
            "rating": 4.9,
            "rating_count": 550,
            "website": "https://fisioterapiayvida.pe/",
            "chain_sites": 2,
        },
        tags=["physiotherapy-segment"],
    )
    base.update(overrides)
    return Prospect(**base)


def test_facts_do_not_crash_on_a_prospect_without_a_registry_score():
    facts = facts_from_prospect(place_prospect())
    assert facts.score_level == "sin puntaje del padron"
    assert facts.category == "sin dato en el registro"
    assert facts.doctors_total is None


def test_facts_carry_what_google_knows_so_the_draft_can_personalize():
    rendered = facts_from_prospect(place_prospect()).render()
    assert "tipo de centro segun Google: Clínica de fisioterapia" in rendered
    assert "calificacion de pacientes: 4.9" in rendered
    assert "cantidad de resenas de pacientes: 550" in rendered
    assert "sucursales de la misma marca: 2" in rendered


def test_a_place_without_chain_does_not_claim_sucursales():
    rendered = facts_from_prospect(place_prospect(google={"cid": "1", "query": "q"})).render()
    assert "sucursales" not in rendered


def test_the_facts_do_not_leak_the_internal_tags():
    """Medido en los borradores reales: el modelo citó `etiqueta physiotherapy-segment` y
    `etiqueta chain` en un mensaje dirigido a un médico. Las etiquetas son para filtrar en el
    CRM, no vocabulario para el cliente."""
    rendered = facts_from_prospect(place_prospect()).render()
    assert "physiotherapy-segment" not in rendered
    assert "etiqueta" not in rendered
    assert "chain" not in rendered


# --- the verifier -----------------------------------------------------------


def test_a_clean_draft_has_no_violations():
    facts = facts_from_prospect(prospect())
    assert verify_draft(clean_draft(), facts=facts, template=TEMPLATE) == ()


def test_verify_rejects_an_invented_quantity():
    """A number the model made up is the classic hallucination in a proposal."""
    draft = clean_draft(
        talking_points=["Con nuestro modelo el retorno estimado es de 2500 soles al mes."]
    )
    violations = verify_draft(draft, facts=facts_from_prospect(prospect()), template=TEMPLATE)
    assert violations
    assert any("2500" in violation for violation in violations)


def test_verify_rejects_a_number_that_only_looks_like_an_allowed_one():
    draft = clean_draft(talking_points=["Atendemos 272 clinicas en el pais."])
    violations = verify_draft(draft, facts=facts_from_prospect(prospect()), template=TEMPLATE)
    assert any("272" in violation for violation in violations)


def test_verify_rejects_a_regulatory_claim_the_template_never_authorized():
    """RNF-06: the model must not promise compliance on its own initiative."""
    draft = clean_draft(
        opening="Contamos con Registro Sanitario vigente y certificado de calibracion."
    )
    violations = verify_draft(draft, facts=facts_from_prospect(prospect()), template=TEMPLATE)
    assert any("registro sanitario" in violation for violation in violations)
    assert any("certificado" in violation for violation in violations)


def test_verify_allows_the_vocabulary_the_owner_put_in_the_template():
    """`comodato` and `ozonoterapia` are in the template, so the model may use them."""
    facts = facts_from_prospect(prospect())
    draft = clean_draft(opening="Le escribo por el modelo de ozonoterapia en comodato.")
    assert verify_draft(draft, facts=facts, template=TEMPLATE) == ()


def test_verify_rejects_a_dose_mention():
    """Doses are the one thing the document forbids the AI to touch at all."""
    draft = clean_draft(opening="Se aplica a una concentracion de 30 ug/ml.")
    violations = verify_draft(draft, facts=facts_from_prospect(prospect()), template=TEMPLATE)
    assert any("concentracion" in violation or "ug/ml" in violation for violation in violations)


def test_quantities_and_terms_helpers():
    assert quantities_in("27 medicos y 3 sedes") == frozenset({"27"})
    assert "registro sanitario" in sensitive_terms_in("con Registro Sanitario vigente")


# --- the template keeps control --------------------------------------------


def test_assembled_message_keeps_the_owners_paragraph_verbatim():
    """The model never produced that paragraph, so it cannot have changed it."""
    message = assemble_message(TEMPLATE, clean_draft())
    assert PARRAFO_DEL_DUEÑO in message
    assert "Unidad de ozonoterapia para su centro medico" in message
    assert "Estimado director medico:" in message


def test_assembly_only_replaces_the_declared_slots():
    message = assemble_message(TEMPLATE, clean_draft(greeting="Hola {subject}"))
    assert "Hola {subject}" in message  # la sustitucion es una sola pasada, por slot


# --- the whole path, with a planted model -----------------------------------


def test_a_hallucinating_model_produces_a_flagged_submission():
    fake_completer.planted = clean_draft(
        talking_points=["Garantizamos un retorno de 1500 soles el primer mes."]
    )
    submission = draft_outreach(
        prospect(), template=TEMPLATE, model="fake/model", completer=fake_completer
    )
    assert submission.status == STATUS_PENDING
    assert submission.violations
    assert submission.is_clean is False


def test_a_honest_model_produces_an_approvable_submission():
    fake_completer.planted = clean_draft()
    submission = draft_outreach(
        prospect(), template=TEMPLATE, model="fake/model", completer=fake_completer
    )
    assert submission.violations == ()
    assert submission.status == STATUS_PENDING

    approved = approve(submission, approver="dueño")
    assert approved.status == STATUS_APPROVED
    assert approved.approver == "dueño"
    assert approved.can_be_sent is True


def test_approval_is_refused_while_the_draft_invented_something():
    """The human is in the loop, not a rubber stamp over a hallucination."""
    fake_completer.planted = clean_draft(opening="Somos lideres con 300 clientes.")
    submission = draft_outreach(
        prospect(), template=TEMPLATE, model="fake/model", completer=fake_completer
    )
    with pytest.raises(ValueError, match="no se puede aprobar"):
        approve(submission, approver="dueño")


# --- la cache de borradores --------------------------------------------------- #
#
# Medido: una corrida de 10 borradores murio en el sexto por un fallo transitorio del proveedor,
# sin dejar mensaje y con los cinco ya pagados perdidos. Ahora cada borrador se guarda por clinica.


def test_a_cached_draft_does_not_call_the_model_again(tmp_path):
    llamadas: list[int] = []

    def contador(**kwargs):
        llamadas.append(1)
        return clean_draft()

    primero = draft_outreach(
        prospect(), template=TEMPLATE, model="fake", completer=contador, cache_dir=tmp_path
    )
    segundo = draft_outreach(
        prospect(), template=TEMPLATE, model="fake", completer=contador, cache_dir=tmp_path
    )

    assert len(llamadas) == 1
    assert segundo.draft.subject == primero.draft.subject
    assert segundo.message == primero.message


def test_a_cached_draft_survives_without_the_model(tmp_path):
    """Una corrida nueva lee lo ya pagado aunque el modelo no este disponible."""

    def contador(**kwargs):
        return clean_draft()

    draft_outreach(
        prospect(), template=TEMPLATE, model="fake", completer=contador, cache_dir=tmp_path
    )

    def no_llamar(**kwargs):
        raise AssertionError("no deberia llamar al modelo: ya estaba cacheado")

    releido = draft_outreach(
        prospect(), template=TEMPLATE, model="fake", completer=no_llamar, cache_dir=tmp_path
    )
    assert releido.prospect_id == "00024663"
    assert releido.violations == ()


def test_the_litellm_call_asks_for_retries_and_a_timeout(monkeypatch):
    """El proveedor reintenta solo lo transitorio: un 429 no puede voltear un lote de diez."""
    from types import SimpleNamespace

    import litellm

    capturado: dict = {}

    def fake_completion(**kwargs):
        capturado.update(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=clean_draft().model_dump_json()))
            ]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    litellm_completer(model="openai/x", system="s", user="u", schema=OutreachDraft)

    assert capturado["num_retries"] >= 2
    assert capturado["timeout"] > 0


# --- una respuesta que no valida no puede voltear el lote --------------------- #
#
# Medido: el modelo devolvio un objeto JSON sin la clave `opening` y esa sola respuesta abandono
# una corrida de diez borradores, perdiendo los cinco ya pagados.


def test_a_reply_without_a_key_is_asked_again_naming_what_was_missing(monkeypatch):
    from types import SimpleNamespace

    import litellm

    respuestas = [
        '{"subject": "s", "greeting": "g", "talking_points": []}',  # sin opening
        clean_draft().model_dump_json(),
    ]
    llamadas: list[dict] = []

    def fake_completion(**kwargs):
        llamadas.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=respuestas.pop(0)))]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    resultado = litellm_completer(model="openai/x", system="s", user="u", schema=OutreachDraft)

    assert isinstance(resultado, OutreachDraft)
    assert len(llamadas) == 2
    correccion = llamadas[1]["messages"][-1]["content"]
    assert "opening" in correccion  # nombra la clave que falto


def test_a_reply_that_never_validates_raises_a_validation_error(monkeypatch):
    """Y se rinde despues de una correccion, no en un bucle infinito."""
    from types import SimpleNamespace

    import litellm
    from pydantic import ValidationError

    llamadas: list[int] = []

    def fake_completion(**kwargs):
        llamadas.append(1)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"subject": "s"}'))]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    with pytest.raises(ValidationError):
        litellm_completer(model="openai/x", system="s", user="u", schema=OutreachDraft)

    assert len(llamadas) == 2  # el intento y la correccion, nada mas


def test_rejection_is_recorded_with_its_reason():
    fake_completer.planted = clean_draft()
    submission = draft_outreach(
        prospect(), template=TEMPLATE, model="fake/model", completer=fake_completer
    )
    rejected = reject(submission, approver="dueño", reason="tono muy comercial")
    assert rejected.status == STATUS_REJECTED
    assert "tono muy comercial" in rejected.approver
    assert rejected.can_be_sent is False


def test_the_submission_lists_what_the_owner_still_has_to_fill():
    fake_completer.planted = clean_draft()
    submission = draft_outreach(
        prospect(), template=TEMPLATE, model="fake/model", completer=fake_completer
    )
    assert submission.missing_human_data == ("[FIRMA DEL DUEÑO]",)


def test_the_prompt_carries_the_facts_and_the_prohibition():
    facts = facts_from_prospect(prospect())
    system, user = build_prompt(facts, TEMPLATE)
    assert "no inventes" in system
    assert "CENTRO MEDICO ESPECIALIZADO SAN FELIPE" in user
    assert "medicos registrados: 27" in user
    assert PARRAFO_DEL_DUEÑO in user


def test_the_module_has_no_send_path():
    """Enforced architecture: sending is the owner's action, one message at a time.

    If somebody adds a `send` here, this test fails and forces the conversation.
    """
    from scraper import copilot

    forbidden = ("send", "send_email", "send_message", "deliver", "publish", "submit_message")
    assert [name for name in forbidden if hasattr(copilot, name)] == []


# --- the owner's template lives in a file -----------------------------------


def test_load_template_reads_the_name_and_the_body(tmp_path):
    path = tmp_path / "mi-plantilla.md"
    path.write_text("---\nname: oaas-prueba\n---\nHola {subject}\n", encoding="utf-8")
    template = load_template(path)
    assert template.name == "oaas-prueba"
    assert template.text == "Hola {subject}\n"


def test_load_template_without_front_matter_falls_back_to_the_file_name(tmp_path):
    path = tmp_path / "otra.md"
    path.write_text("Solo texto {opening}\n", encoding="utf-8")
    template = load_template(path)
    assert template.name == "otra"
    assert template.text == "Solo texto {opening}\n"


def test_the_shipped_template_declares_every_slot():
    """The file the deployment actually reads must be usable as it stands."""
    from pathlib import Path

    template = load_template(Path(__file__).resolve().parents[1] / "templates" / "outreach-oaas.md")
    assert template.name
    for slot in template.slots:
        assert "{" + slot + "}" in template.text
    # El dueño tiene que completar la firma antes de que el mensaje pueda salir.
    assert template.text.count("[") >= 1


def test_submission_to_dict_carries_the_findings_and_the_draft():
    fake_completer.planted = clean_draft(opening="Somos lideres con 300 clientes.")
    submission = draft_outreach(
        prospect(), template=TEMPLATE, model="fake/model", completer=fake_completer
    )
    payload = submission_to_dict(submission)
    assert payload["status"] == STATUS_PENDING
    assert payload["violations"]
    assert payload["missing_human_data"] == ["[FIRMA DEL DUEÑO]"]
    assert "300 clientes" in payload["message"]


# --- the LiteLLM adapter, with the provider stubbed --------------------------


def test_litellm_completer_passes_the_schema_and_parses_the_response(monkeypatch):
    """The one part that talks to a provider. Stubbed, so the mapping is verified
    without a key: the schema travels as `response_format` and the reply is validated."""
    from types import SimpleNamespace

    import litellm

    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        content = clean_draft().model_dump_json()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    result = litellm_completer(model="groq/llama", system="s", user="u", schema=OutreachDraft)

    assert isinstance(result, OutreachDraft)
    assert captured["model"] == "groq/llama"
    assert captured["response_format"] is OutreachDraft
    assert [message["role"] for message in captured["messages"]] == ["system", "user"]


def test_litellm_completer_passes_the_custom_endpoint_and_key(monkeypatch):
    """The NaN API is reached with an api_base, exactly as its own docs describe."""
    from types import SimpleNamespace

    import litellm

    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        content = clean_draft().model_dump_json()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    litellm_completer(
        model="openai/deepseek-v4-flash",
        system="s",
        user="u",
        schema=OutreachDraft,
        api_base="https://api.nan.builders/v1",
        api_key="sk-nan",
    )

    assert captured["api_base"] == "https://api.nan.builders/v1"
    assert captured["api_key"] == "sk-nan"


def test_litellm_completer_degrades_when_the_provider_rejects_the_schema(monkeypatch):
    """An OpenAI-compatible endpoint LiteLLM does not know may refuse a JSON schema.

    The guarantee is the local Pydantic validation, so losing server-side enforcement
    costs nothing that matters and must not break the run.
    """
    from types import SimpleNamespace

    import litellm

    attempts: list[dict] = []

    def fake_completion(**kwargs):
        attempts.append(dict(kwargs))
        if isinstance(kwargs.get("response_format"), type):
            raise Exception("400 Bad Request: response_format json_schema unsupported")
        content = clean_draft().model_dump_json()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    result = litellm_completer(
        model="openai/deepseek-v4-flash", system="s", user="u", schema=OutreachDraft
    )

    assert isinstance(result, OutreachDraft)
    assert len(attempts) == 2
    assert attempts[1]["response_format"] == {"type": "json_object"}


def test_litellm_completer_remembers_the_format_that_worked(monkeypatch):
    """Discovery is paid once per process, not once per draft."""
    from types import SimpleNamespace

    import litellm

    attempts: list[dict] = []

    def fake_completion(**kwargs):
        attempts.append(dict(kwargs))
        if isinstance(kwargs.get("response_format"), type):
            raise Exception("400: response_format json_schema unsupported")
        content = clean_draft().model_dump_json()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    for _ in range(2):
        litellm_completer(
            model="openai/deepseek-v4-flash", system="s", user="u", schema=OutreachDraft
        )

    assert len(attempts) == 3  # 2 en la primera, 1 en la segunda


def test_litellm_completer_honours_a_pinned_format(monkeypatch):
    """With the format pinned there is exactly one call, and no rejected attempt."""
    from types import SimpleNamespace

    import litellm

    attempts: list[dict] = []

    def fake_completion(**kwargs):
        attempts.append(dict(kwargs))
        content = clean_draft().model_dump_json()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    monkeypatch.setattr(litellm, "completion", fake_completion)
    litellm_completer(
        model="openai/deepseek-v4-flash",
        system="s",
        user="u",
        schema=OutreachDraft,
        response_format="json_object",
    )

    assert len(attempts) == 1
    assert attempts[0]["response_format"] == {"type": "json_object"}


def test_a_pinned_format_that_fails_does_not_silently_degrade(monkeypatch):
    """Pinning is a decision: if it fails, say so instead of trying something else."""
    from types import SimpleNamespace

    import litellm

    def fake_completion(**kwargs):
        raise Exception("400: response_format json_object unsupported")

    monkeypatch.setattr(litellm, "completion", fake_completion)
    with pytest.raises(Exception, match="json_object"):
        litellm_completer(
            model="openai/x",
            system="s",
            user="u",
            schema=OutreachDraft,
            response_format="json_object",
        )


def test_the_prompt_asks_for_json_by_name():
    """A provider in json_object mode needs the word JSON in the prompt."""
    _, user = build_prompt(facts_from_prospect(prospect()), TEMPLATE)
    assert "JSON" in user
