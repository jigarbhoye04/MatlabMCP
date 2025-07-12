# MATLAB MCP Integration

This is an implementation of a Model Context Protocol (MCP) server for MATLAB. It allows MCP clients (like LLM agents or Claude Desktop) to interact with a shared MATLAB session using the MATLAB Engine API for Python.

## Features

*   **Execute MATLAB Code:** Run arbitrary MATLAB code snippets via the `runMatlabCode` tool.
*   **Retrieve Variables:** Get the value of variables from the MATLAB workspace using the `getVariable` tool.
*   **Structured Communication:** Tools return results and errors as structured JSON for easier programmatic use by clients.
*   **Non-Blocking Execution:** MATLAB engine calls are run asynchronously using `asyncio.to_thread` to prevent blocking the server.
*   **Standard Logging:** Uses Python's standard `logging` module, outputting to `stderr` for visibility in client logs.
*   **Shared Session:** Connects to an existing shared MATLAB session.

> [!TIP]
> MatlabMCP wikipedia by DEVIN.
 Checkout [DeepWiki](https://deepwiki.com/jigarbhoye04/MatlabMCP) for more detailed and illustrative information about architecture.

## Requirements

*   Python 3.12 or higher
*   MATLAB (**R2023a or higher recommended** - check MATLAB Engine API for Python compatibility) with the MATLAB Engine API for Python installed.
*   `numpy` Python package.

## Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/jigarbhoye04/MatlabMCP.git
    cd MatlabMCP
    ```

2.  Set up a Python virtual environment (recommended):
    ```bash
    # Install uv if you haven't already: https://github.com/astral-sh/uv
    uv init
    uv venv
    source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
    ```

3.  Install dependencies:
    ```bash
    uv pip sync
    ```

4.  Ensure MATLAB is installed and the MATLAB Engine API for Python is configured for your Python environment. See [MATLAB Documentation](https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html).

5.  **Start MATLAB and share its engine:** Run the following command in the MATLAB Command Window:
    ```matlab
    matlab.engine.shareEngine
    ```
    You can verify it's shared by running `matlab.engine.isEngineShared` in MATLAB (it should return `true` or `1`). The MCP server needs this shared engine to connect.

## Configuration (for Claude Desktop)

To use this server with Claude Desktop:

1.  Go to Claude Desktop -> Settings -> Developer -> Edit Config.
2.  This will open `claude_desktop_config.json`. Add or modify the `mcpServers` section to include the `MatlabMCP` configuration:

    ```json
    {
      "mcpServers": {
        "MatlabMCP": {
          "command": "C:\\Users\\username\\.local\\bin\\uv.exe", // Path to your uv executable
          "args": [
            "--directory",
            "C:\\Users\\username\\Desktop\\MatlabMCP\\", // ABSOLUTE path to the cloned repository directory
            "run",
            "main.py"
          ]
          // Optional: Add environment variables if needed
          // "env": {
          //   "MY_VAR": "value"
          // }
        }
        // Add other MCP servers here if you have them
      }
    }
    ```
3.  **IMPORTANT:** Replace `C:\\Users\\username\\...` paths with the correct **absolute paths** for your system.
4.  Save the file and **restart Claude Desktop**.
5.  **Logging:** Server logs (from Python's `logging` module) will appear in Claude Desktop's MCP log files (accessible via `tail -f ~/Library/Logs/Claude/mcp-server-MatlabMCP.log` on macOS or checking `%APPDATA%\Claude\logs\` on Windows).


## Development

Project Structure:
```
MatlabMCP/
├── .venv/                     # Virtual environment created by uv
├── Docs/
│   └── Images/
│   └── Updates.md             # Documentation for updates and changes
├── main.py                    # The MCP server script
├── pyproject.toml             # Project metadata and dependencies
├── README.md                  # This file
└── uv.lock                    # Lock file for dependencies
```

## Documentation
Check out [Updates](./Docs/Updates.md) for detailed documentation on the server's features, usage, and development notes.

## Contributing
Contributions are welcome! If you have any suggestions or improvements, feel free to open an issue or submit a pull request.

Let's make this even better together!
