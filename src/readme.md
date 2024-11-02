# CoAgents Research Canvas Example

Live demo: https://examples-coagents-research-canvas-ui.vercel.app/

---

## Running the Agent

**These instructions assume you are in the `coagents-research-canvas/` directory**

### Prerequisites
- Python 3.12 or higher
- Poetry (package manager)

First, ensure you have the correct Python version:
```sh
python --version  # Should be 3.12 or higher
```

If you need to install Python 3.12, you can:
- Download it from [python.org](https://www.python.org/downloads/)
- Or use pyenv: `pyenv install 3.12`

Then install the dependencies:
```sh
cd agent
poetry env use python3.12  # Explicitly specify Python 3.12
poetry install
```

Then, create a `.env` file inside `./agent` with the following:
```
OPENAI_API_KEY=...
TAVILY_API_KEY=...
```

IMPORTANT:
Make sure the OpenAI API Key you provide, supports gpt-4o.

Then, run the demo:

```sh
poetry run demo
```

## Running the UI

First, install the dependencies:

```sh
cd ./ui
pnpm i
```

Then, create a `.env` file inside `./ui` with the following:
```
OPENAI_API_KEY=...
```

Then, run the Next.js project:

```sh
pnpm run dev
```

## Usage

Navigate to [http://localhost:3000](http://localhost:3000).


# LangGraph Studio

Run LangGraph studio, then load the `./agent` folder into it.

Make sure to create the `.env` mentioned above first!




# Troubleshooting

A few things to try if you are running into trouble:

1. Make sure there is no other local application server running on the 8000 port.
2. Under `/agent/my_agent/demo.py`, change `0.0.0.0` to `127.0.0.1` or to `localhost`
