# Date: 09-04-2025 (Major)

## Implemented Tools

### `getVariable`

Retrieves the value of a specified variable from the active MATLAB workspace.

**MCP Tool Name:** `getVariable`

**Arguments:**

*   `variable_name` (string): The exact name of the variable to retrieve from the MATLAB workspace.

**Returns (JSON):**

*   **On Success:**
    ```json
    {
      "status": "success",
      "variable": "<variable_name>",
      "value": <converted_value>
    }
    ```
    Where `<converted_value>` is the variable's value converted to a JSON-serializable Python type (e.g., number, string, boolean, list). See **Data Type Conversion** below.
*   **On Failure:**
    ```json
    {
      "status": "error",
      "error_type": "<ErrorType>",
      "message": "<error_message>"
    }
    ```
    Common `ErrorType` values include:
    *   `KeyError`: Variable not found in the workspace.
    *   `EngineError`: Problem communicating with the MATLAB engine.
    *   `TypeError`: The retrieved MATLAB value could not be serialized to JSON after conversion.
    *   `RuntimeError`: No active MATLAB session found.

**Data Type Conversion (`matlab_to_python`):**

The server attempts to convert common MATLAB data types to their Python equivalents for JSON serialization:

*   **Numeric Scalars/Arrays (`double`):** Converted to Python `float` or `list` of `float` (nested for matrices). Singleton dimensions are squeezed.
*   **Logical Scalars/Arrays (`logical`):** Converted to Python `bool` or `list` of `bool`.
*   **Character Arrays (`char`):** Converted to Python `string`.
*   **Other Types:** Basic support might exist, but complex types like structs, cell arrays, or objects may return a string representation or cause a serialization error.

**Successful Test Cases:**

The following scenarios were tested and passed successfully using an LLM client connected via MCP:

1.  **Retrieve Numeric Scalar:**
    *   MATLAB Code: `myNum = 99.5;`
    *   Tool Call: `getVariable(variable_name="myNum")`
    *   Result: `{"status": "success", ..., "value": 99.5}`
2.  **Retrieve String:**
    *   MATLAB Code: `myGreeting = 'Welcome!';`
    *   Tool Call: `getVariable(variable_name="myGreeting")`
    *   Result: `{"status": "success", ..., "value": "Welcome!"}`
3.  **Retrieve Numeric Vector:**
    *   MATLAB Code: `myVec = [10, 20, 30];`
    *   Tool Call: `getVariable(variable_name="myVec")`
    *   Result: `{"status": "success", ..., "value": [10.0, 20.0, 30.0]}`
4.  **Retrieve Numeric Matrix:**
    *   MATLAB Code: `myMatrix = [1 2; 3 4];`
    *   Tool Call: `getVariable(variable_name="myMatrix")`
    *   Result: `{"status": "success", ..., "value": [[1.0, 2.0], [3.0, 4.0]]}`
5.  **Variable Not Found:**
    *   Tool Call: `getVariable(variable_name="nonexistent")`
    *   Result: `{"status": "error", "error_type": "KeyError", ...}`
6.  **Retrieve After Previous Error:** Ensured `getVariable` could still retrieve existing variables even if a preceding `runMatlabCode` call failed due to a MATLAB error.

---

> Stay tuned for more updates!
> This document will be updated as new features and tools are implemented.

# Date: 13-04-2025 (Minor)

## Integrate Deeper MCP Features

The goal is to allow MCP clients to:
- Discover .m files located in a specific directory on the machine running the server.
- Read the content of those .m files.