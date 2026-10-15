"""Resolution of the search API key, and where it is expected to live.

`.env` is a local convenience for development: in Cloud Run the same variables
arrive from Secret Manager and no file exists. The resolver is the only place that
knows the variable names, so a missing key always produces the same instruction
instead of a provider-specific crash deep inside a request.
"""

import pytest

from scraper.config import (
    SEARCH_PROVIDERS,
    MissingCredentialsError,
    resolve_llm_endpoint,
    resolve_search_credentials,
)

KEY_VARIABLES = tuple(SEARCH_PROVIDERS.values())


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """No test may depend on a real .env sitting in the working tree."""
    for variable in KEY_VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.delenv("CONFIA2_SEARCH_PROVIDER", raising=False)
    for variable in (
        "CONFIA2_LLM_MODEL",
        "CONFIA2_LLM_API_BASE",
        "CONFIA2_LLM_API_KEY_VAR",
        "CONFIA2_LLM_RESPONSE_FORMAT",
        "NAN_API_KEY",
        "NAN_API_KEY ",  # como lo deja podman --env-file si en .env sobra un espacio
        "SERPER_API_KEY ",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        monkeypatch.delenv(variable, raising=False)


def test_resolves_the_provider_named_by_the_environment(monkeypatch):
    monkeypatch.setenv("CONFIA2_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("SERPER_API_KEY", "clave-de-prueba")
    assert resolve_search_credentials() == ("serper", "clave-de-prueba")


def test_infers_the_provider_when_only_one_key_is_present(monkeypatch):
    """Pasting a single key should be enough for the enrichment to work."""
    monkeypatch.setenv("BRAVE_API_KEY", "clave-brave")
    assert resolve_search_credentials() == ("brave", "clave-brave")


def test_ignores_a_key_that_is_present_but_empty(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "   ")
    with pytest.raises(MissingCredentialsError):
        resolve_search_credentials()


def test_missing_key_fails_with_the_exact_instruction(monkeypatch):
    with pytest.raises(MissingCredentialsError) as error:
        resolve_search_credentials()
    assert "SERPER_API_KEY" in str(error.value)
    assert ".env" in str(error.value)


def test_naming_an_unknown_provider_lists_the_known_ones(monkeypatch):
    monkeypatch.setenv("CONFIA2_SEARCH_PROVIDER", "bing")
    with pytest.raises(MissingCredentialsError) as error:
        resolve_search_credentials()
    assert "serper" in str(error.value)


def test_two_keys_require_an_explicit_choice(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "una")
    monkeypatch.setenv("BRAVE_API_KEY", "otra")
    with pytest.raises(MissingCredentialsError) as error:
        resolve_search_credentials()
    assert "CONFIA2_SEARCH_PROVIDER" in str(error.value)


# --- the model endpoint (NaN is OpenAI-compatible) -------------------------- #


def test_nan_is_used_when_its_key_is_the_only_one_present(monkeypatch):
    """`NAN_API_KEY` alone is enough, with the documented base URL and starting model."""
    monkeypatch.setenv("NAN_API_KEY", "sk-nan")
    endpoint = resolve_llm_endpoint()
    assert endpoint.model == "openai/deepseek-v4-flash"
    assert endpoint.api_base == "https://api.nan.builders/v1"
    assert endpoint.api_key == "sk-nan"


def test_a_configured_model_keeps_litellm_resolving_the_provider(monkeypatch):
    """Setting a model must not drag in the NaN endpoint."""
    monkeypatch.setenv("CONFIA2_LLM_MODEL", "groq/llama-3.3-70b-versatile")
    monkeypatch.setenv("NAN_API_KEY", "sk-nan")
    endpoint = resolve_llm_endpoint()
    assert endpoint.model == "groq/llama-3.3-70b-versatile"
    assert endpoint.api_base is None
    assert endpoint.api_key is None


def test_a_custom_base_url_gets_the_openai_prefix(monkeypatch):
    """LiteLLM routes an OpenAI-compatible endpoint by the `openai/` prefix."""
    monkeypatch.setenv("CONFIA2_LLM_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("CONFIA2_LLM_API_BASE", "https://api.nan.builders/v1")
    monkeypatch.setenv("NAN_API_KEY", "sk-nan")
    endpoint = resolve_llm_endpoint()
    assert endpoint.model == "openai/deepseek-v4-flash"
    assert endpoint.api_base == "https://api.nan.builders/v1"


def test_an_already_prefixed_model_is_not_prefixed_twice(monkeypatch):
    monkeypatch.setenv("CONFIA2_LLM_MODEL", "openai/deepseek-v4-flash")
    monkeypatch.setenv("CONFIA2_LLM_API_BASE", "https://api.nan.builders/v1")
    monkeypatch.setenv("NAN_API_KEY", "sk-nan")
    assert resolve_llm_endpoint().model == "openai/deepseek-v4-flash"


def test_an_explicit_model_wins_over_the_environment(monkeypatch):
    monkeypatch.setenv("CONFIA2_LLM_MODEL", "groq/llama")
    monkeypatch.setenv("NAN_API_KEY", "sk-nan")
    assert resolve_llm_endpoint(model="openrouter/algo").model == "openrouter/algo"


def test_a_custom_endpoint_without_its_key_fails_with_the_variable_name(monkeypatch):
    monkeypatch.setenv("CONFIA2_LLM_API_BASE", "https://api.nan.builders/v1")
    with pytest.raises(MissingCredentialsError) as error:
        resolve_llm_endpoint()
    assert "NAN_API_KEY" in str(error.value)


def test_the_api_key_variable_can_be_named_explicitly(monkeypatch):
    monkeypatch.setenv("CONFIA2_LLM_API_BASE", "https://otro.example/v1")
    monkeypatch.setenv("CONFIA2_LLM_MODEL", "algo-grande")
    monkeypatch.setenv("CONFIA2_LLM_API_KEY_VAR", "OTRO_KEY")
    monkeypatch.setenv("OTRO_KEY", "clave-otro")
    endpoint = resolve_llm_endpoint()
    assert endpoint.api_key == "clave-otro"
    assert endpoint.api_base == "https://otro.example/v1"
    assert endpoint.model == "openai/algo-grande"


def test_the_description_never_leaks_the_key(monkeypatch):
    monkeypatch.setenv("NAN_API_KEY", "sk-secreto-que-no-debe-salir")
    texto = resolve_llm_endpoint().describe()
    assert "sk-secreto" not in texto
    assert "deepseek-v4-flash" in texto
    assert "api.nan.builders" in texto


def test_without_any_configuration_the_document_default_is_used():
    endpoint = resolve_llm_endpoint()
    assert endpoint.model.startswith("gemini/")
    assert endpoint.api_base is None
    assert endpoint.response_format == "auto"


# --- el formato de respuesta ------------------------------------------------ #
#
# Medido: la API de NaN respondió 400 a `response_format` con esquema estricto y aceptó
# modo JSON. Volver a intentar el esquema en cada corrida cuesta un request y ensucia el
# log con un banner de error que parece un problema del proveedor y no lo es.


def test_the_nan_default_pins_json_mode_from_what_was_measured(monkeypatch):
    monkeypatch.setenv("NAN_API_KEY", "sk-nan")
    assert resolve_llm_endpoint().response_format == "json_object"


def test_the_response_format_can_be_pinned_explicitly(monkeypatch):
    monkeypatch.setenv("NAN_API_KEY", "sk-nan")
    monkeypatch.setenv("CONFIA2_LLM_RESPONSE_FORMAT", "schema")
    assert resolve_llm_endpoint().response_format == "schema"


def test_an_unknown_response_format_is_rejected(monkeypatch):
    monkeypatch.setenv("CONFIA2_LLM_RESPONSE_FORMAT", "yaml")
    with pytest.raises(ValueError, match="yaml"):
        resolve_llm_endpoint()


def test_a_configured_provider_keeps_auto_discovery(monkeypatch):
    monkeypatch.setenv("CONFIA2_LLM_MODEL", "groq/llama")
    assert resolve_llm_endpoint().response_format == "auto"


# --- el espacio de mas alrededor del '=' en .env ----------------------------
#
# Medido: `NAN_API_KEY =sk-...` en .env lo tolera python-dotenv pero no
# `podman --env-file`, que le pasa al contenedor el nombre CON el espacio. Adentro la
# variable queda invisible y el sintoma es "falta la clave", que manda a buscar al lado
# equivocado.


def test_a_variable_that_only_differs_by_a_space_is_named_in_the_error(monkeypatch):
    monkeypatch.setenv("NAN_API_KEY ", "sk-nan")
    with pytest.raises(MissingCredentialsError) as error:
        resolve_llm_endpoint(api_base="https://api.nan.builders/v1")
    message = str(error.value)
    assert "NAN_API_KEY" in message
    assert "espacio" in message


def test_the_same_hint_applies_to_the_search_key(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY ", "clave")
    with pytest.raises(MissingCredentialsError) as error:
        resolve_search_credentials()
    assert "espacio" in str(error.value)


def test_a_clean_environment_produces_no_such_hint(monkeypatch):
    with pytest.raises(MissingCredentialsError) as error:
        resolve_search_credentials()
    assert "espacio" not in str(error.value)
