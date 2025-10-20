# Claude Code Configuration for Talkative Project

> **IMPORTANT**: This configuration imports and follows rules from `.cursor/agent-rules/` to ensure consistency across AI assistants (Claude Code, Cursor, etc.).

## Imported Agent Rules

@import "../.cursor/agent-rules/commit.mdc"
@import "../.cursor/agent-rules/commit-fast.mdc"
@import "../.cursor/agent-rules/pr-review.mdc"
@import "../.cursor/agent-rules/check.mdc"
@import "../.cursor/agent-rules/bug-fix.mdc"
@import "../.cursor/agent-rules/analyze-issue.mdc"
@import "../.cursor/agent-rules/implement-task.mdc"
@import "../.cursor/agent-rules/mermaid.mdc"
@import "../.cursor/agent-rules/clean.mdc"
@import "../.cursor/agent-rules/code-analysis.mdc"
@import "../.cursor/agent-rules/create-docs.mdc"
@import "../.cursor/agent-rules/update-docs.mdc"
@import "../.cursor/agent-rules/add-to-changelog.mdc"
@import "../.cursor/agent-rules/context-prime.mdc"
@import "../.cursor/agent-rules/continuous-improvement.mdc"
@import "../.cursor/agent-rules/create-command.mdc"
@import "../.cursor/agent-rules/five.mdc"
@import "../.cursor/agent-rules/docs-alignment.mdc"
@import "../.cursor/agent-rules/architecture-docs.mdc"
@import "../.cursor/agent-rules/version-history.mdc"

---

## Additional Claude-Specific Notes

### MCP Integration
This project has MCP servers configured for enhanced capabilities:
- **Supabase MCP**: Direct database operations (see `.claude/mcp.json`)
- **Render MCP**: Deployment and service management (optional)

See [MCP_SETUP.md](.claude/MCP_SETUP.md) for configuration details.

When MCP tools are available, prefer using them for:
- Database queries: Use `mcp__supabase__*` tools instead of Python client
- Deployments: Use `mcp__render__*` tools for Render operations

### Documentation Management

**CRITICAL: Always keep documentation up to date**

After completing ANY implementation, bug fix, or significant change:

1. **Identify Affected Documentation**:
   - Check `docs/` directory for related documentation files
   - Common files to update:
     - `docs/README.md` - Main project documentation
     - `docs/docs/TESTING.md` - Test documentation
     - `docs/docs/LOCAL_SETUP.md` - Setup instructions
     - `docs/docs/references/SESSION_SUMMARY.md` - Session work summary
     - `docs/VERSION.md` - Version history
     - `docs/flow.md` - Architecture diagrams

2. **Update Documentation with Summary**:
   - Add a summary section at the top of relevant docs explaining what changed
   - Update any outdated information in the document body
   - Add code examples if applicable
   - Update diagrams if architectural changes were made
   - Include file paths and line numbers for code references

3. **Documentation Format**:
   ```markdown
   ## Recent Updates

   ### [Date] - [Change Title]
   **Summary**: Brief description of what changed and why

   **Files Modified**:
   - `file/path.py:123-145` - Description of change

   **Impact**: How this affects users/developers
   ```

4. **Always Update These Files**:
   - If you modify tests → Update `docs/docs/TESTING.md`
   - If you fix a bug → Add entry to `docs/docs/references/SESSION_SUMMARY.md`
   - If you change configuration → Update `docs/docs/LOCAL_SETUP.md`
   - If you add features → Update `docs/README.md` and `docs/VERSION.md`
   - **If you modify API endpoints** → Update `docs/docs/reference/API_DESIGN.md`

5. **API Development Requirements**:
   **CRITICAL: When adding or modifying API endpoints, you MUST**:

   a. **Write Unit Tests FIRST** (or immediately after implementation):
      - Create test file in `tests/backend/api/test_<module>_api.py`
      - Test all success cases (200, 201, 204)
      - Test all error cases (400, 404, 422, 500)
      - Test validation boundaries (min/max values, enum options)
      - Test request/response models match spec
      - Aim for 100% endpoint coverage

   b. **Update API Documentation**:
      - Add new endpoints to `docs/docs/reference/API_DESIGN.md`
      - Include in "Recent Updates" section at top with date
      - Document request/response schemas
      - Provide example requests and responses
      - Note any breaking changes
      - Link to test files

   c. **Update Database Schema** (if database changes):
      - Create/update SQL schema files in `database/`
      - Include detailed column comments
      - Add constraints, indexes, triggers
      - Document default values and valid ranges

   **Example Workflow**:
   ```
   1. Implement API endpoint
   2. Write comprehensive unit tests
   3. Run tests: `uv run python -m pytest tests/backend/api/test_<module>_api.py -v`
   4. Update docs/docs/reference/API_DESIGN.md with "Recent Updates" entry
   5. Update database/ schema if needed
   6. Commit all changes together (code + tests + docs + schema)
   ```

   **This is NOT optional** - PRs without tests and documentation updates will be rejected.


### Tool Usage
- Use `TodoWrite` tool to track multi-step tasks
- Use `Task` tool for complex research or searches that may require multiple rounds
- Always run tests with `uv run python -m pytest <path> -v`
- Validate Mermaid diagrams with `npx -p @mermaid-js/mermaid-cli mmdc -i <input>.md -o test.md`
- **Update corresponding documentation AFTER finishing implementation** (see Documentation Management above)

### Package Management & Development Commands
**IMPORTANT: Always use `uv` and `Makefile` for this project**

- **Package Installation**: Use `uv pip install <package>` instead of `pip install`
- **Running Commands**: Use `make <target>` for common operations (see Makefile)
- **Server Startup**: Use `make run-server` instead of direct uvicorn commands
- **Environment Files**: All credentials are in `env_files/*.env` directory
  - `env_files/supabase.env` - Supabase database credentials
  - `env_files/upstash.env` - Redis cache credentials
  - `env_files/render.env` - Render deployment config
- **Merging env files**: Use `make env-merge` to merge all env files into `backend/.env`

Key Makefile targets:
- `make run-server` - Start FastAPI backend on port 8000
- `make src` - Run the original voice agent (src.main)
- `make install` - Install production dependencies
- `make install-dev` - Install dev dependencies
- `make test-backend` - Run backend tests
- `make lint` - Run code linting
- `make format` - Format code with black/isort
- `make clean` - Clean build artifacts
- `make help` - See all available commands

### Communication Style
- Be concise and direct
- Minimize preamble and postamble
- Provide complete information matching task complexity
- Use code references with `file_path:line_number` format

### Git Operations
- Follow conventional commit format with emojis (as defined in commit.mdc)
- Never skip hooks unless explicitly requested
- Always check authorship before amending commits
- Create well-structured PRs with clear descriptions
