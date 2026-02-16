import os
import json
from dotenv import load_dotenv
from azure.identity import AzureCliCredential, get_bearer_token_provider
from openai import AzureOpenAI
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

# Azure OpenAI setup using same auth as demo_agent.py
credential = AzureCliCredential()
token_provider = get_bearer_token_provider(
    credential, "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token_provider=token_provider,
    api_version="2024-12-01-preview",
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

app = FastAPI()

POS_NAMES = [
    "top-left", "top-center", "top-right",
    "middle-left", "center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
]


class MoveRequest(BaseModel):
    board: list[str | None]  # 9 cells: "X", "O", or null
    player: str              # "X" or "O"
    instructions: str        # human instructions for this agent


def board_to_text(board: list[str | None]) -> str:
    rows = []
    for r in range(3):
        cells = []
        for c in range(3):
            v = board[r * 3 + c]
            cells.append(v if v else ".")
        rows.append(" | ".join(cells))
    return "\n---------\n".join(rows)


def build_prompt(board, player, instructions):
    opponent = "O" if player == "X" else "X"
    board_str = board_to_text(board)

    empty_positions = [POS_NAMES[i] for i, v in enumerate(board) if v is None]

    return f"""You are an AI agent playing Tic-Tac-Toe as "{player}" against opponent "{opponent}".

Current board:
{board_str}

Position names (3x3 grid):
top-left    | top-center    | top-right
middle-left | center        | middle-right
bottom-left | bottom-center | bottom-right

Available positions: {", ".join(empty_positions)}

Your coach's instructions: {instructions if instructions.strip() else "No specific instructions — play your best."}

Think step by step about the best move. Consider:
1. Can you win immediately?
2. Do you need to block the opponent from winning?
3. What strategic position is best given your coach's instructions?

Respond with ONLY valid JSON in this exact format:
{{"thinking": "your reasoning here (2-3 sentences)", "move": "position-name"}}

The move MUST be one of the available positions listed above. Do not pick an occupied cell."""


@app.post("/api/move")
async def get_move(req: MoveRequest):
    if len(req.board) != 9:
        raise HTTPException(400, "Board must have 9 cells")
    if req.player not in ("X", "O"):
        raise HTTPException(400, "Player must be X or O")

    empty = [i for i, v in enumerate(req.board) if v is None]
    if not empty:
        raise HTTPException(400, "No empty cells")

    prompt = build_prompt(req.board, req.player, req.instructions)

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a tic-tac-toe playing agent. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=200,
        )

        text = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0].strip()

        data = json.loads(text)
        move_name = data.get("move", "").strip().lower()
        thinking = data.get("thinking", "")

        # Map position name to index
        move_index = -1
        for i, name in enumerate(POS_NAMES):
            if name == move_name:
                move_index = i
                break

        if move_index < 0 or move_index not in empty:
            # LLM gave invalid move — pick first available
            move_index = empty[0]
            thinking += f" (LLM chose invalid position '{move_name}', falling back to {POS_NAMES[move_index]})"

        return {"move": move_index, "thinking": thinking, "position": POS_NAMES[move_index]}

    except Exception as e:
        # Fallback: pick first empty cell
        move_index = empty[0]
        return {
            "move": move_index,
            "thinking": f"LLM error: {str(e)}. Falling back to {POS_NAMES[move_index]}.",
            "position": POS_NAMES[move_index],
        }


# Serve static files from docs/
app.mount("/", StaticFiles(directory="docs", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("Starting Agent Games server at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
