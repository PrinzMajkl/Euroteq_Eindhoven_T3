# Project Rules & Guidelines

These rules apply to all AI agents and contributors working in this repository.

## 1. Language Rule
- **Strict English Content**: All repository content must be written in **English**. This includes:
  - Documentation and Markdown files
  - Code, code comments, and docstrings
  - Presentation slides, scripts, and brainstorming notes
  - Commit messages and pull request descriptions
- *Note*: You may converse with the user in their preferred language (e.g., Czech) during chat if they prompt in that language, but all artifacts, commits, and files saved into the repository must be in English.

## 2. Directory Structure & Separation of Concerns
The repository is strictly divided into three primary functional areas:
1. **`code/`**: Source code, technical implementation, scripts, tests, dependencies, and configuration.
2. **`presentation/`**: Slide outlines, brainstorming documents, pitch structure, talking points, and presentation assets.
3. **`general_information/`**: Project brief, problem statements, requirements, background research, mentor feedback, and team notes.

Do not place arbitrary files in the repository root. The root should only contain project-level index and configuration files (e.g., `README.md`, `AGENTS.md`, `GEMINI.md`, `.gitignore`).

## 3. AI Accessibility & Knowledge Organization
- **Structured & Modular**: Keep documents focused and logically segmented. When a document grows large, split sub-topics into separate Markdown files within the corresponding directory.
- **Predictable File Naming**: Use snake_case or kebab-case for filenames, avoiding spaces and special characters (e.g., `slides_brainstorm.md`, `problem_statement.md`).
- **Indices & Cross-Linking**: Every subdirectory must have a `README.md` acting as a navigation index linking to relevant documents in that folder.
- **Scannable Formatting**: Use standard GitHub-flavored Markdown with clear headings (`#`, `##`, `###`), bullet points, and tables where applicable to ensure optimal token efficiency and semantic clarity for AI models.
