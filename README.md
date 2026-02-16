# agent-games

AI agent-based games powered by Azure OpenAI. Watch LLM agents compete against each other while you coach them with natural language instructions.

## Games

- **Tic-Tac-Toe** — Two LLM agents play on a 3×3 grid. Give each agent strategic instructions and watch them reason through each move.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

## Configuration

Create a `.env` file (or use the existing one):

```
AZURE_OPENAI_ENDPOINT="https://your-resource.cognitiveservices.azure.com"
AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
```

Authentication uses `AzureCliCredential` — make sure you're logged in:

```bash
az login
```

## Running

```bash
python main.py
```

Open http://localhost:8000 in your browser.

## How It Works

- The frontend sends the board state and your coaching instructions to the backend
- The backend calls Azure OpenAI with a prompt that asks the LLM to reason about its move
- The LLM's thinking is displayed in real-time in the "Agent thinking" panel
- Each agent independently reasons about strategy based on your instructions
