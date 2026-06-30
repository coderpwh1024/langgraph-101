# Repository Guidelines

## Project Structure & Module Organization

This repository is a LangChain/LangGraph learning workspace organized around runnable examples and supporting notes.

- `notebooks/101/`: introductory LangChain and LangGraph scripts, summaries, and generated images.
- `notebooks/201/`: deeper agent examples, including multi-agent, email-agent, memory-graph, and deep-agents demos.
- `notebooks/utils/`: shared Python helpers such as model configuration and graph utilities.
- `docs/`: higher-level learning notes.
- `translate/`: translation source files and localized output.
- `CLAUDE.md`: detailed local style and review rules; follow it for Python changes.

## Build, Test, and Development Commands

There is no central build system or dependency lock file in this repo. Run examples directly from the repository root.

- `python notebooks/101/101_langchain_langgraph.py`: run an introductory example.
- `python notebooks/201/multi_agent.py`: run the multi-agent demo.
- `python notebooks/201/deep_agents.py`: run the deep-agents examples.
- `python -m compileall notebooks`: syntax-check all Python files.

Most scripts require environment variables loaded from `.env`, especially `DASHSCOPE_API_KEY`.

## Coding Style & Naming Conventions

Use Google Python style with 4-space indentation. Prefer line lengths under 80 characters; up to 100 is acceptable for teaching examples and prompts. Use `lower_with_under` for modules, functions, variables, and LangGraph node names; use `CapWords` for classes and `CAPS_WITH_UNDER` for constants.

Keep comments, docstrings, and prompts primarily in Chinese. Keep identifiers and technical API names in English. Import shared model instances from `utils.models` instead of hard-coding API keys, model URLs, or credentials in example scripts.

## Testing Guidelines

No formal test suite is currently present. For changes to examples, run the edited script and `python -m compileall notebooks`. If adding tests, use `pytest`, place tests under `tests/`, and name files `test_<module>.py`. Keep tests focused on helper functions, graph routing logic, and tool behavior that can run without external API calls.

## Commit & Pull Request Guidelines

Recent commits use Conventional Commit prefixes, often with a scoped Chinese description, for example `feat: deep_agents 新增...`, `chore: deep_agents 注释...`, and `docs: deep_agents 新增...`. Follow that pattern.

Pull requests should include a short purpose statement, changed files or examples, required environment variables, and commands run for verification. Include screenshots or generated asset paths when image or graph output changes.

## Security & Configuration Tips

Do not commit `.env` files or real API keys. Prefer parameterized SQL in new examples; if a teaching snippet uses string interpolation for SQL, clearly mark it as non-production code.
