"""La proyección que lee la pantalla: los nombres que espera el frontend, desde el contrato.

Lo que se prueba acá es sobre todo lo que la proyección **no** hace: no inventa el nombre del
director médico, no afirma nada sobre la competencia y no devuelve a `descubierto` un lead que el
dueño ya movió.
"""

from types import SimpleNamespace

from scraper.contract import Prospect
from scraper.copilot import DraftSubmission, OutreachDraft
from scraper.ui_projection import ESTADO_EN_LA_PANTALLA, lead_document, sugerencia, write_leads
from tests.test_firestore import FakeFirestore


def del_padron(**overrides) -> Prospect:
    base = dict(
        id="00010292",
        origin="renipress",
        ipress_code="00010292",
        name="CENTRO MEDICO ESPECIALIZADO SAN FELIPE",
        institution="PRIVADO",
        category="I-4",
        classification="CENTROS DE SALUD CON CAMAS DE INTERNAMIENTO",
        establishment_type="ESTABLECIMIENTO DE SALUD CON INTERNAMIENTO",
        location={"department": "LIMA", "province": "LIMA", "district": "LURIGANCHO", "ubigeo": "150118"},
        contact={"phone": "987243367", "phone_valid": True, "address": "JR. PUNO 182", "schedule": ""},
        capacity={"doctors_total": 27, "period": "2026-08"},
        score={"total": 100, "level": "high", "components": {}, "measured_weight": 100},
        tags=["target-profile", "priority-high"],
    )
    base.update(overrides)
    return Prospect(**base)


def del_segmento(**overrides) -> Prospect:
    base = dict(
        id="places:16002912900950143659",
        origin="places",
        name="Artrauma",
        location={"department": "LIMA", "district": "HUAURA"},
        contact={"phone": "993 923 680", "phone_valid": True, "address": "Av. Uno 100"},
        google={
            "cid": "1",
            "query": "q",
            "category": "Clínica de fisioterapia",
            "rating": 4.8,
            "rating_count": 553,
            "chain_sites": 2,
            "website": "https://artrauma.com.pe/",
        },
        tags=["physiotherapy-segment", "chain"],
    )
    base.update(overrides)
    return Prospect(**base)


def test_la_proyeccion_usa_los_nombres_que_espera_la_pantalla():
    lead = lead_document(del_segmento())
    assert lead["id"] == "places:16002912900950143659"
    assert lead["name"] == "Artrauma"
    assert lead["district"] == "Huaura"
    assert lead["status"] == "descubierto"
    assert lead["phone"] == "993 923 680"
    assert lead["outboundDraft"] is None


def test_el_director_medico_queda_nulo_porque_ningun_dato_lo_trae():
    """El mock del frontend lo inventó; la proyección no puede."""
    lead = lead_document(del_padron())
    assert lead["directorMedico"] is None
    assert lead["doctorSpecialty"] is None


def test_la_especialidad_sale_de_la_categoria_de_google():
    assert lead_document(del_segmento())["specialty"] == "Clínica de fisioterapia"
    # Sin categoría de búsqueda cae al tipo de establecimiento del padrón, que es otra cosa. Y viene
    # en mayúsculas del origen: «Centros De Salud Con Camas De Internamiento» es peor que esto.
    assert lead_document(del_padron())["specialty"] == "Centros de salud con camas de internamiento"


def test_las_dos_formas_del_contrato_salen_con_la_misma_forma_para_la_pantalla():
    """Es el punto del módulo: la página no tiene que saber que hay dos orígenes."""
    claves_padron = set(lead_document(del_padron()))
    claves_segmento = set(lead_document(del_segmento()))
    assert claves_padron == claves_segmento


def test_la_sugerencia_no_afirma_nada_sobre_la_competencia():
    """El mock decía «sin ozonoterapia», y eso no lo podemos sostener por clínica."""
    texto = sugerencia(del_segmento()) or ""
    assert "ozono" not in texto.lower()
    assert "553 reseñas" in texto
    assert "2 sucursales" in texto


def test_el_canal_sugerido_es_telefono_porque_no_hay_ningun_email():
    submission = DraftSubmission(
        prospect_id="places:1",
        template_name="oaas-v1",
        model="m",
        draft=OutreachDraft(subject="Asunto", greeting="Hola:", opening="Le escribimos."),
        message="Asunto\n\nHola:\n\nLe escribimos.\n\n[FIRMA DEL DUEÑO]\n",
    )
    lead = lead_document(del_segmento(), submission=submission)
    assert lead["outboundDraft"]["suggestedChannel"] == "Teléfono"
    assert lead["outboundDraft"]["subject"] == "Asunto"
    assert lead["outboundDraft"]["missingHumanData"] == ["[FIRMA DEL DUEÑO]"]
    assert lead["hasAiDraft"] is True
    assert lead["draftApproved"] is False


def test_el_telefono_dice_si_esta_verificado():
    """La página muestra el teléfono; sin este campo no puede distinguir uno verificado de uno dudoso."""
    assert lead_document(del_segmento())["phoneValid"] is True
    verificado = del_segmento(contact={"phone": "993", "phone_valid": False})
    assert lead_document(verificado)["phoneValid"] is False


def test_una_corrida_nueva_no_revierte_la_aprobacion_del_dueno():
    """Defecto que encontró un verificador independiente, y de la familia que yo estaba protegiendo.

    `draftApproved` se recalculaba desde el borrador **de esta corrida**, que siempre nace pendiente:
    el dueño aprobaba en la página y la corrida siguiente lo devolvía a `false`. Quedaba `approvals`
    diciendo «aprobado» y `leads` diciendo «no aprobado», con la decisión humana borrada de la
    tarjeta. El test anterior solo miraba `approvals.status`, y por eso no lo veía.
    """
    client = FakeFirestore()
    lead = del_segmento()
    write_leads([lead], client=client, log=lambda *_: None)

    client.documents("leads")[lead.id]["draftApproved"] = True  # el dueño aprobó desde la página

    write_leads(
        [lead],
        client=client,
        submissions=[un_borrador(prospect_id=lead.id)],
        log=lambda *_: None,
    )

    assert client.documents("leads")[lead.id]["draftApproved"] is True


def test_la_ingesta_no_devuelve_a_descubierto_un_lead_que_el_dueno_ya_movio():
    client = FakeFirestore()
    write_leads([del_segmento()], client=client, log=lambda *_: None)

    guardado = client.documents("leads")["places:16002912900950143659"]
    guardado["status"] = "propuesta enviada"
    guardado["statusNote"] = "lo movió el dueño"

    write_leads([del_segmento(name="Artrauma Renovada")], client=client, log=lambda *_: None)

    guardado = client.documents("leads")["places:16002912900950143659"]
    assert guardado["status"] == "propuesta enviada"
    assert guardado["statusNote"] == "lo movió el dueño"
    assert guardado["name"] == "Artrauma Renovada"  # lo que sí es de la ingesta


def test_los_estados_son_exactamente_los_del_tipo_de_la_pagina():
    """`PipelineStatus` en `src/types/index.ts` del repo de la pagina: el Kanban ubica las tarjetas
    por ese string.

    Comparar contra el mock no alcanzaba: el mock solo usa `'descubierto'`, asi que el desajuste de
    `'propuesta enviada'` contra `'propuesta_enviada'` era invisible — la tarjeta no caeria en
    ninguna columna. Se compara contra el TIPO, que es el consumidor real.
    """
    assert sorted(ESTADO_EN_LA_PANTALLA.values()) == [
        "cierre",
        "contactado",
        "descubierto",
        "propuesta_enviada",
    ]
    assert set(ESTADO_EN_LA_PANTALLA) == {"discovered", "contacted", "proposal_sent", "contract_signed"}


# --- la pantalla de aprobacion, que es la que el dueno usa todos los dias ------- #
#
# El mock del frontend guarda los borradores con otra forma (`aiContent` como objeto, `type`,
# `createdBy`) y los identifica como `{id}-outbound`. Con la forma del contrato, su componente no
# encontraba ninguno de los diez borradores reales.


def un_borrador(prospect_id: str = "places:16002912900950143659", **overrides) -> DraftSubmission:
    base = dict(
        prospect_id=prospect_id,
        template_name="oaas-v1",
        model="openai/deepseek-v4-flash",
        draft=OutreachDraft(
            subject="Ozonoterapia en comodato para Artrauma",
            greeting="Estimado equipo de Artrauma:",
            opening="Le escribimos porque figura como clinica de fisioterapia.",
        ),
        message="Ozonoterapia en comodato para Artrauma\n\nEstimado equipo:\n\nLe escribimos.\n\n[FIRMA DEL DUENO]\n",
    )
    base.update(overrides)
    return DraftSubmission(**base)


def test_la_pantalla_de_aprobacion_encuentra_la_forma_que_espera():
    from scraper.ui_projection import write_approvals

    client = FakeFirestore()
    write_approvals([un_borrador()], client=client, log=lambda *_: None)

    doc = client.documents("approvals")["places:16002912900950143659-outbound"]
    assert doc["id"] == "places:16002912900950143659-outbound"
    assert doc["prospectId"] == "places:16002912900950143659"
    assert doc["type"] == "outbound"
    assert doc["status"] == "pending_approval"
    assert doc["createdBy"] == "confia2-ingesta"
    assert doc["aiContent"]["subject"] == "Ozonoterapia en comodato para Artrauma"
    assert doc["aiContent"]["body"].startswith("Ozonoterapia en comodato")
    assert doc["aiContent"]["recipientRole"] == "Dirección médica"
    # El tipo de la pagina (`aiContent: OutboundDraft`) exige este campo.
    assert doc["aiContent"]["suggestedChannel"] == "Teléfono"
    # El mock ponia «Dra. Valdivia»: ninguna fuente trae un nombre de persona.
    assert doc["aiContent"]["recipientName"] is None
    assert doc["missingHumanData"] == ["[FIRMA DEL DUENO]"]


def test_la_pantalla_puede_deshabilitar_aprobar_cuando_hay_hallazgos():
    from scraper.ui_projection import write_approvals

    client = FakeFirestore()
    write_approvals(
        [un_borrador(violations=("cantidad inventada: 40%",))], client=client, log=lambda *_: None
    )
    doc = client.documents("approvals")["places:16002912900950143659-outbound"]
    assert doc["hasViolations"] is True
    assert doc["violations"] == ["cantidad inventada: 40%"]


def test_la_decision_del_dueno_sobre_un_borrador_sobrevive_a_una_corrida_nueva():
    from scraper.ui_projection import write_approvals

    client = FakeFirestore()
    write_approvals([un_borrador()], client=client, log=lambda *_: None)

    guardado = client.documents("approvals")["places:16002912900950143659-outbound"]
    guardado["status"] = "approved"
    guardado["approvedBy"] = "diego.andia.f@gmail.com"

    write_approvals([un_borrador(message="Otro texto regenerado.\n")], client=client, log=lambda *_: None)

    guardado = client.documents("approvals")["places:16002912900950143659-outbound"]
    assert guardado["status"] == "approved"
    assert guardado["approvedBy"] == "diego.andia.f@gmail.com"
    assert "regenerado" in guardado["aiContent"]["body"]  # lo que si es del job se actualiza


# --- los fantasmas del segmento ----------------------------------------------- #
#
# El segmento de Places no devuelve el mismo conjunto en cada corrida con la misma consulta:
# medido, 829 un dia, 791 y despues 774. Como la ingesta solo hace upsert, los que no vuelven a
# aparecer se quedan. No son basura —son clinicas reales que aparecieron antes— y borrar en un CRM es
# irreversible: se marcan, no se borran.


def test_un_lead_que_la_corrida_no_vio_se_marca_y_no_se_borra():
    from scraper.ui_projection import repair_leads

    client = FakeFirestore()
    visto = del_segmento()
    write_leads([visto], client=client, log=lambda *_: None)
    client.documents("leads")[visto.id]["updatedAt"] = "2026-10-14T22:29+00:00"

    # uno de una corrida anterior, que esta no volvio a ver
    client.data.setdefault("leads", {})["places:999"] = {
        "id": "places:999",
        "origin": "places",
        "segment": "fisioterapia",
        "tags": ["physiotherapy-segment"],
        "updatedAt": "2026-10-14T20:07+00:00",
        "stale": False,
    }

    counts = repair_leads(client=client, seen_since="2026-10-14T22:20", log=lambda *_: None)

    assert counts["al_dia"] == 1
    assert counts["viejos"] == 1
    # los dos ya estaban al dia en la etiqueta, asi que solo se reescribio el que cambio de marca
    assert counts["escritos"] == 1
    assert client.documents("leads")["places:999"]["stale"] is True
    assert client.documents("leads")[visto.id]["stale"] is False
    assert len(client.documents("leads")) == 2  # se marca, no se borra


def test_los_documentos_anteriores_reciben_el_campo_aunque_no_lo_tuvieran():
    """La pantalla va a filtrar por `stale == false`, y un documento sin el campo no apareceria nunca."""
    from scraper.ui_projection import repair_leads

    client = FakeFirestore()
    client.data.setdefault("leads", {})["viejo"] = {
        "id": "viejo",
        "origin": "renipress",
        "updatedAt": "2026-10-14T22:29+00:00",
    }

    counts = repair_leads(client=client, seen_since="2026-10-14T22:20", log=lambda *_: None)

    assert counts["al_dia"] == 1
    assert client.documents("leads")["viejo"]["stale"] is False
    assert client.documents("leads")["viejo"]["segment"] == "padron"


def test_la_etiqueta_de_segmento_distingue_las_tres_clases():
    """Son **tres**, no dos, y la tercera importa: un resultado de busqueda que no entro al segmento
    NO viene del registro de SUSALUD, asi que llamarlo "padron" es una procedencia falsa."""
    assert lead_document(del_padron())["segment"] == "padron"
    assert lead_document(del_segmento())["segment"] == "fisioterapia"

    fuera_del_segmento = del_segmento(id="places:999", tags=["chain"])
    assert lead_document(fuera_del_segmento)["segment"] == "busqueda"


def test_la_reparacion_corrige_la_etiqueta_vieja_y_no_solo_la_marca():
    """Los que quedaron como "padron" siendo de busqueda se corrigen sin volver a scrapear."""
    from scraper.ui_projection import repair_leads

    client = FakeFirestore()
    client.data.setdefault("leads", {})["places:999"] = {
        "id": "places:999",
        "origin": "places",
        "tags": ["chain"],  # resultado de Places que NO entro al segmento
        "segment": "padron",  # la etiqueta vieja, y falsa
        "updatedAt": "2026-10-14T22:29+00:00",
        "stale": False,
    }

    counts = repair_leads(client=client, seen_since="2026-10-14T22:20", log=lambda *_: None)

    assert counts["escritos"] == 1  # solo la etiqueta cambio
    assert client.documents("leads")["places:999"]["segment"] == "busqueda"


def test_un_lead_recien_escrito_nace_al_dia():
    assert lead_document(del_segmento())["stale"] is False


def test_repair_sin_proyecto_se_corta_antes_de_tocar_nada(capsys):
    """Sin `--firestore-project` no hay a donde conectarse: se corta, no se adivina."""
    from scraper.__main__ import main

    assert main(["--repair-leads"]) == 1
    assert "firestore-project" in capsys.readouterr().err


# --- el cableado al pipeline ------------------------------------------------- #
#
# En Cloud Run este bloque es la unica copia: los JSON viven en /tmp y no sobreviven al contenedor.
# Por eso se prueba entero, con las tres colecciones, y no cada escritor por su lado.


def test_una_corrida_escribe_las_tres_colecciones():
    from scraper.contract import ProspectArchive
    from scraper.pipeline import write_to_firestore

    client = FakeFirestore()
    padron, segmento = del_padron(), del_segmento()
    archivo = ProspectArchive(
        generated_at="2026-10-14T00:00:00+00:00", total=1, prospects=[padron]
    )
    informe = SimpleNamespace(
        archive=ProspectArchive(
            generated_at="2026-10-14T00:00:00+00:00", total=1, prospects=[segmento]
        )
    )
    submission = DraftSubmission(
        prospect_id=segmento.id,
        template_name="oaas-v1",
        model="openai/deepseek-v4-flash",
        draft=OutreachDraft(subject="Asunto", greeting="Hola:", opening="Le escribimos."),
        message="Asunto\n\nHola:\n\nLe escribimos.\n\n[FIRMA DEL DUENO]\n",
    )

    counts = write_to_firestore(
        archive=archivo,
        informe=informe,
        submissions=[submission],
        store=client,
        log=lambda *_: None,
    )

    assert len(client.documents("prospects")) == 2  # el contrato, con los dos origenes
    assert len(client.documents("proposals")) == 1  # el borrador, para el CRM
    assert len(client.documents("leads")) == 2  # la proyeccion, una sola forma
    assert len(client.documents("approvals")) == 1  # la pantalla de aprobacion
    assert counts["leads_nuevos"] == 2
    assert counts["approvals_nuevos"] == 1

    lead = client.documents("leads")[segmento.id]
    assert lead["status"] == "descubierto"
    assert lead["directorMedico"] is None
    assert lead["outboundDraft"]["subject"] == "Asunto"
    assert set(client.documents("leads")[padron.id]) == set(lead)
