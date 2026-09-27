from fastapi import APIRouter

from app import schemas
from app.services import guidelines

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/guidelines", response_model=schemas.AssistantGuidelines)
def get_guidelines():
    """Regras fixas da MarIA, para o painel mostrar ao lado dos campos da profissional."""
    return schemas.AssistantGuidelines(
        assistant_name=guidelines.ASSISTANT_NAME,
        voice_questions=guidelines.VOICE_QUESTIONS,
        never_say=guidelines.NEVER_SAY_DEFAULTS,
        risk_behaviors=guidelines.RISK_BEHAVIORS,
        pronoun_options=[{"key": key, "label": item["label"]} for key, item in guidelines.PRONOUNS.items()],
    )
