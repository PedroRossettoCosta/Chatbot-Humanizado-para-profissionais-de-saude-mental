from types import SimpleNamespace

from app.services import guidelines, llm


def _professional(**fields):
    base = dict(
        name="Ana Teste",
        voice_tone=None,
        audience_description=None,
        service_info=None,
        voice_examples=None,
        extra_never_say=None,
        pronouns=None,
        working_hours=None,
        session_minutes=None,
        calendar_connection=None,
    )
    base.update(fields)
    return SimpleNamespace(**base)


def test_prompt_introduces_maria_and_keeps_fixed_never_say():
    prompt = llm.build_system_prompt(_professional(), [])
    assert "Você é a MarIA" in prompt
    assert "inteligência artificial" in prompt
    for item in guidelines.NEVER_SAY_DEFAULTS:
        assert item in prompt


def test_extra_never_say_is_added_after_the_fixed_list():
    prompt = llm.build_system_prompt(_professional(extra_never_say=["Falar do meu ex-sócio.", "  "]), [])
    assert "- Falar do meu ex-sócio." in prompt
    assert prompt.index(guidelines.NEVER_SAY_DEFAULTS[-1]) < prompt.index("Falar do meu ex-sócio.")
    assert "-   \n" not in prompt


def test_about_and_service_info_are_always_in_the_prompt():
    prompt = llm.build_system_prompt(
        _professional(audience_description="Psicanalista, atende adultos.", service_info="R$ 200 a sessão."),
        [],
    )
    assert "Psicanalista, atende adultos." in prompt
    assert "R$ 200 a sessão." in prompt


def test_missing_profile_fields_are_marked_as_not_provided():
    prompt = llm.build_system_prompt(_professional(), [])
    assert prompt.count(llm.NOT_PROVIDED) == 2
    assert "EXEMPLOS DE RESPOSTA" not in prompt


def test_examples_follow_the_fixed_question_order_and_skip_empty_pairs():
    prompt = llm.build_system_prompt(
        _professional(
            voice_examples={
                "momento_dificil": {"good": "Sinto muito. Posso te contar como funciona.", "bad": "Calma."},
                "preco": {"good": "A sessão custa R$ 200.", "bad": ""},
                "funcionamento": {"good": "", "bad": ""},
            }
        ),
        [],
    )
    assert "EXEMPLOS DE RESPOSTA" in prompt
    assert prompt.index("Quanto custa a consulta?") < prompt.index("momento muito difícil")
    assert "Como funciona o seu atendimento?" not in prompt
    assert "Resposta ruim (evite este estilo): Calma." in prompt
    assert prompt.count("Resposta ruim") == 1


def test_pronouns_follow_the_professionals_choice():
    feminine = llm.build_system_prompt(_professional(pronouns="feminine"), [])
    assert "sempre no feminino: ela, dela" in feminine

    masculine = llm.build_system_prompt(_professional(pronouns="masculine"), [])
    assert "sempre no masculino: ele, dele" in masculine


def test_without_choice_the_prompt_is_neutral():
    prompt = llm.build_system_prompt(_professional(), [])
    assert "sempre pelo nome: não use pronomes" in prompt


def test_prompt_states_the_session_length_for_any_name():
    prompt = llm.build_system_prompt(_professional(session_minutes=50), [])
    assert "Duração de cada sessão: 50 minutos" in prompt
    assert "sessão, consulta ou atendimento" in prompt
    unknown = llm.build_system_prompt(_professional(), [])
    assert "A duração da sessão não foi informada" in unknown
