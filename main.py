import sys
import json
import asyncio
import logging
import numpy as np
from typing import Any, Dict, List 
import tempfile 
import os

# MCP specific imports
from mcp.server.fastmcp import FastMCP
import mcp.types as types


logging.basicConfig(
    level=logging.INFO, # Set to DEBUG for more verbose output
    stream=sys.stderr,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("MatlabMCP")

import matlab.engine
mcp = FastMCP("MatlabMCP") 

# --- MATLAB Engine Connection ---
logger.info("Finding shared MATLAB sessions...")
names = matlab.engine.find_matlab()
logger.info(f"Found sessions: {names}")

eng = None
if not names:
    logger.error("No shared MATLAB sessions found. This server requires a shared MATLAB session.")
    logger.error("Please start MATLAB and run 'matlab.engine.shareEngine' in its Command Window.")
    sys.exit(1) # Exit if no MATLAB found
else:
    session_name = names[0]
    logger.info(f"Attempting to connect to MATLAB session: {session_name}")
    try:
        eng = matlab.engine.connect_matlab(session_name)
        logger.info(f"Successfully connected to shared MATLAB session: {session_name}")
    except matlab.engine.EngineError as e:
        logger.error(f"Error connecting to MATLAB session '{session_name}': {e}", exc_info=True)
        sys.exit(1) # Exit if connection fails
    except Exception as e: # Catch any other unexpected connection error
        logger.error(f"An unexpected error occurred while trying to connect to MATLAB: {e}", exc_info=True)
        sys.exit(1)

if eng is None: # Should not be reached if sys.exit(1) was hit, but as a safeguard
    logger.critical("MATLAB engine 'eng' is None after connection attempt. Exiting.")
    sys.exit(1)

# --- Helper Function ---
def matlab_to_python(data: Any) -> Any:
    """
    Converts common MATLAB data types returned by the engine into JSON-Serializable Python types.
    """
    if isinstance(data, (str, int, float, bool, type(None))):
        return data
    elif isinstance(data, matlab.double):
        np_array = np.array(data).squeeze()
        if np_array.ndim == 0: return float(np_array)
        return np_array.tolist() # Handles vectors and matrices to lists/nested lists
    elif isinstance(data, matlab.logical):
        np_array = np.array(data).squeeze()
        if np_array.ndim == 0: return bool(np_array)
        return np_array.tolist()
    elif isinstance(data, matlab.char):
        return str(data)
    else:
        logger.warning(f"Unsupported MATLAB type encountered for conversion: {type(data)}. Attempting string representation.")
        try:
            return str(data)
        except Exception as e_str_conv:
            logger.error(f"Could not convert type {type(data)} to string: {e_str_conv}")
            return f"Unserializable MATLAB Type: {type(data)}"
    # --- TODO: Add more MATLAB types like structs, cell arrays, tables ---

# --- Tool Definitions ---
@mcp.tool()
async def runMatlabCode(code: str) -> Dict[str, Any]:
    """
    Runs arbitrary MATLAB code in the shared MATLAB session.
    WARNING: Executing arbitrary code can be a security risk.
    This tool attempts execution via a temporary file first, then falls back to eng.evalc() to capture output.

    Args:
        code: The MATLAB code string to execute.

    Returns:
        A dictionary with:
        - "status": "success" or "error"
        - "output": (on success) A message indicating success or the captured output from eng.evalc().
        - "error_type": (on error) The type of Python exception.
        - "stage": (on error) The stage of execution where the error occurred.
        - "message": (on error) A detailed error message.
    """
    logger.info(f"runMatlabCode request: {code[:150]}...") # Log a bit more of the code

    if not eng: # Should be caught at startup, but good check
        logger.error("runMatlabCode: MATLAB engine not available.")
        return {"status": "error", "error_type": "RuntimeError", "message": "MATLAB engine not available."}

    temp_file_path = None
    try:
        # --- Attempt 1: Execute using a temporary .m file ---
        # This is often more robust for multi-line scripts or function definitions
        with tempfile.NamedTemporaryFile(mode="w", suffix=".m", delete=False, encoding='utf-8') as tmp:
            tmp.write(code)
            temp_file_path = tmp.name
        logger.debug(f"Attempting to run code via temporary file: {temp_file_path}")
        # Run blocking MATLAB call in a thread
        await asyncio.to_thread(eng.run, temp_file_path, nargout=0)
        logger.info(f"Code executed successfully using temporary file: {temp_file_path}")
        return {"status": "success", "output": f"Code executed successfully via temporary file ({os.path.basename(temp_file_path)})."}

    except matlab.engine.MatlabExecutionError as e_run:
        # This error means MATLAB itself had an issue running the code in the temp file
        logger.warning(f"Temporary file execution failed: {e_run}. Attempting eng.evalc() as fallback...")

        # --- Attempt 2: Fallback to eng.evalc() to capture output ---
        try:
            result = await asyncio.to_thread(eng.evalc, code)
            logger.info("Code executed successfully using eng.evalc() fallback.")
            return {"status": "success", "output": result}
        except matlab.engine.MatlabExecutionError as e_evalc:
            logger.error(f"eng.evalc() fallback also failed: {e_evalc}", exc_info=True)
            return {
                "status": "error", "error_type": "MatlabExecutionError",
                "stage": "evalc_fallback",
                "message": f"MATLAB execution failed (tried temp file then evalc): {str(e_evalc)}"
            }
        except Exception as e_evalc_other: # Catch other errors during evalc
            logger.error(f"Unexpected error during eng.evalc() fallback: {e_evalc_other}", exc_info=True)
            return {
                "status": "error", "error_type": e_evalc_other.__class__.__name__,
                "stage": "evalc_fallback",
                "message": f"Unexpected error during eng.evalc() fallback: {str(e_evalc_other)}"
            }

    except matlab.engine.EngineError as e_eng: # Errors related to engine communication
        logger.error(f"MATLAB Engine communication error in runMatlabCode: {e_eng}", exc_info=True)
        return {"status": "error", "error_type": "EngineError", "message": f"MATLAB Engine error: {str(e_eng)}"}
    except IOError as e_io: # Catch errors related to temp file I/O
        logger.error(f"IOError during temporary file operation for runMatlabCode: {e_io}", exc_info=True)
        return {"status": "error", "error_type": "IOError", "message": f"File operation error: {str(e_io)}"}
    except Exception as e_outer: # Catch-all for other unexpected errors
        logger.error(f"Unexpected error in runMatlabCode: {e_outer}", exc_info=True)
        return {"status": "error", "error_type": e_outer.__class__.__name__, "message": f"An unexpected error occurred: {str(e_outer)}"}
    finally:
        # --- Cleanup: Ensure temporary file is deleted ---
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except OSError as e_cleanup:
                logger.warning(f"Could not clean up temporary file {temp_file_path}: {e_cleanup}")


@mcp.tool()
async def getVariable(variable_name: str) -> Dict[str, Any]:


    """
    Gets the value of a variable from the MATLAB workspace.

    Args:
        variable_name: The name of the variable to retrieve.

    Returns:
        A dictionary with:
        - "status": "success" or "error"
        - "variable": (on success) The name of the variable.
        - "value": (on success) The JSON-serializable value of the variable.
        - "error_type": (on error) The type of Python exception.
        - "message": (on error) A detailed error message.
    """



    logger.info(f"getVariable request for: '{variable_name}'")

    if not eng: # Should be caught at startup
        logger.error("getVariable: MATLAB engine not available.")
        return {"status": "error", "error_type": "RuntimeError", "message": "MATLAB engine not available."}
    if not variable_name or not isinstance(variable_name, str): # Basic input validation
        logger.warning(f"getVariable: Invalid variable_name provided: {variable_name}")
        return {"status": "error", "error_type": "ValueError", "message": "Invalid variable_name: must be a non-empty string."}

    try:
        # Synchronous part for asyncio.to_thread
        def get_var_from_matlab_sync():
            # Check if variable exists directly in the workspace
            if variable_name not in eng.workspace:
                raise KeyError(f"Variable '{variable_name}' not found in MATLAB workspace.")
            return eng.workspace[variable_name]

        matlab_value = await asyncio.to_thread(get_var_from_matlab_sync)
        python_value = matlab_to_python(matlab_value)

        # Test JSON serialization of the converted value
        try:
            json.dumps({"test_value": python_value}) # Wrapped in a dict for a robust test
            logger.info(f"Successfully retrieved and converted variable '{variable_name}'.")
            return {"status": "success", "variable": variable_name, "value": python_value}
        except TypeError as json_err:
            logger.error(f"Serialization Error: Failed to serialize MATLAB value for '{variable_name}' (type: {type(matlab_value)}, py_type: {type(python_value)}) after conversion: {json_err}", exc_info=True)
            return {
                "status": "error", "error_type": "TypeError",
                "message": f"Value for variable '{variable_name}' could not be JSON serialized after conversion. Original MATLAB type: {type(matlab_value)}"
            }

    except KeyError as ke: # Variable not found
        logger.warning(f"getVariable: {ke}")
        return {"status": "error", "error_type": "KeyError", "message": str(ke)}
    except matlab.engine.EngineError as e_eng:
        logger.error(f"MATLAB Engine error during getVariable for '{variable_name}': {e_eng}", exc_info=True)
        return {"status": "error", "error_type": "EngineError", "message": f"MATLAB Engine error: {str(e_eng)}"}
    except Exception as e:
        logger.error(f"Unexpected error in getVariable for '{variable_name}': {e}", exc_info=True)
        return {"status": "error", "error_type": e.__class__.__name__, "message": f"An unexpected error occurred: {str(e)}"}


if __name__ == "__main__":
    logger.info("Starting MATLAB MCP server...")
    # mcp.run() blocks until shutdown
    mcp.run(transport='stdio')
    # This line will only execute AFTER the server has stopped.
    logger.info("MATLAB MCP Server has shut down.")