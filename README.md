# AISpring Tools V2 Project

## Project Overview
This project is a collection of tools and mini-applications developed under the AISpring initiative, including snake game implementations, void agent modules, webpage components, and test scripts for various functionalities.

## Directory Structure
| Directory/File | Description |
|----------------|-------------|
| `cpp_projects/` | C++示例项目和代码 |
| `python_snake_game/` | Python-based Snake game implementation |
| `snake_game/` | Another version or related resources for the Snake game |
| `void-main/` | Core module for the Void agent functionality |
| `webpage/` | Webpage-related resources or front-end components |
| `logs/` | Storage directory for application logs |
| `__pycache__/` | Compiled Python files (auto-generated) |
| `.trae/` | Configuration or temporary files directory |
| `.voidrules` | Project-specific rules and guidelines |
| `v2_1.py` | Main script for version 2.1 of the toolset |
| `v2_void.py` | Void agent-related script |
| `test_doubao.py` | Test script for Doubao service/tool integration |
## Key Files Explanation
- `cpp_projects/`: C++示例项目，包含基本的C++编程示例和构建配置
- `v2_1.py`: Entry point for the main functionality of version 2.1, containing core logic for the toolset.
- `v2_void.py`: Implements basic Void agent functionalities such as command handling and validation.
- `test_doubao.py`: Tests integration with the Doubao service, including API calls and functionality checks.

## Usage Notes
1. **Port Occupancy**: If a port is occupied, the program is in hot deployment state—do not re-run the program.
2. **Git Sync**: After modifying code, always sync changes using:
   ```bash
   git add .
   git commit -m "Your change description (in Chinese)"
   git push
   ```
3. **Console Encoding**: Ensure the console uses UTF-8 encoding when running scripts to avoid character display issues.
4. **Windows Compatibility**: Optimized for Windows 11 systems.
5. **Indentation Debugging**: When using the agent's `read_file` on Python files, each line includes `[s=<spaces> t=<tabs>]` to make hidden indentation explicit.
6. **Batch Approval**: When the agent proposes multiple tasks, you can approve them once with `y` (once) or `a` (always) instead of confirming each task repeatedly.
7. **Auto Indent for Python**: In `edit_lines`, you can set `<auto_indent>true</auto_indent>` to align inserted code to surrounding indentation automatically.
8. **Better Glob Matching**: Patterns like `dir/**/*.py` now also match `dir/file.py` (no intermediate subdirectory).
9. **Modification Stats**: File modification stats are aggregated per file and printed only once for incremental new changes (not repeated every chat, and rollback won’t block future stats).
10. **Terminal Info**: Each `run_command` now prints a `Terminal ID` and output summary to the console. If the process keeps running (or times out), it also prints a running terminal summary.
 
## Important Rules
Refer to the `.voidrules` file for detailed project rules and guidelines.
