from fastapi import APIRouter
from modules.prompt_manager import list_prompts, get_prompt, save_prompt, delete_prompt

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("")
async def list_all_prompts():
    return {"prompts": list_prompts()}


@router.get("/{prompt_id}")
async def get_one_prompt(prompt_id: str):
    p = get_prompt(prompt_id)
    if not p:
        return {"error": "not found"}
    return p


@router.post("")
async def create_or_update_prompt(data: dict):
    return save_prompt(data)


@router.delete("/{prompt_id}")
async def delete_one_prompt(prompt_id: str):
    ok = delete_prompt(prompt_id)
    return {"ok": ok}
