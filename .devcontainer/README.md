# Dev Container Setup for Harness Migration Toolkit

This directory contains the VS Code Dev Container configuration for the Harness Migration Toolkit. Using this dev container ensures a consistent development environment with all required dependencies pre-installed.

## What's Included

- **Python 3.11** - Latest stable Python version
- **Required Dependencies** - Automatically installs from `requirements.txt`:
  - `requests>=2.31.0` - For HTTP API calls
  - `prompt_toolkit>=3.0.0` - For interactive CLI interface
- **VS Code Extensions**:
  - Python language support
  - Code formatting (autopep8)
  - Linting (flake8, pylint)
  - JSON/YAML support
  - Code runner for testing snippets
- **Git and GitHub CLI** - For version control operations

## Getting Started

### Prerequisites
- [VS Code](https://code.visualstudio.com/) installed
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) installed
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running

### Usage

1. Open the `harness_migration_toolkit` folder in VS Code
2. VS Code should automatically detect the dev container configuration
3. Click "Reopen in Container" when prompted, or:
   - Open Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
   - Type "Dev Containers: Reopen in Container"
   - Select the command

### First Time Setup

The container will automatically:
1. Install Python dependencies from `requirements.txt`
2. Make the `setup.sh` script executable
3. Set up the Python environment

After the container starts, you can:
1. Run the interactive migration: `python3 harness_pipeline_migration.py --interactive`
2. Or set up config file first: `./setup.sh`

### Benefits

- **Isolated Environment** - No conflicts with your local Python setup
- **Consistent Dependencies** - Same versions across all development machines
- **Pre-configured Tools** - Linting, formatting, and debugging ready to go
- **Easy Sharing** - Team members get identical development environment

### Customization

You can modify `.devcontainer/devcontainer.json` to:
- Change Python version
- Add additional VS Code extensions
- Modify container settings
- Add environment variables

### Troubleshooting

If you encounter issues:
1. Ensure Docker Desktop is running
2. Try "Dev Containers: Rebuild Container" from Command Palette
3. Check that the `requirements.txt` file exists in the root directory
4. Verify VS Code has the Dev Containers extension installed

For more information, see the [VS Code Dev Containers documentation](https://code.visualstudio.com/docs/remote/containers).
