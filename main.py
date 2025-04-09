from typing import Any,Dict
from mcp.server.fastmcp import FastMCP
import sys
import logging
import asyncio
import numpy as np
import json

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # timestamp, logger name, level, message
)

logger = logging.getLogger("MatlabMCP")

import matlab.engine
mcp = FastMCP("MatlabMCP")


logger.info("Finding shared MATLAB sessions...")
names = matlab.engine.find_matlab()
logger.info(f"Found sessions: {names}")

if not names:
    logger.error("No shared MATLAB sessions found.")
    logger.error("Please start MATLAB and run 'matlab.engine.shareEngine' in its Command Window.")
    sys.exit(0)
else:
    session_name = names[0] 
    logger.info(f"Connecting to session: {session_name}")
    try:
        eng = matlab.engine.connect_matlab(session_name)
        logger.info("Successfully connected to shared MATLAB session.")
    except matlab.engine.EngineError as e:
        logger.error(f"Error connecting or communicating with MATLAB: {e}")
        sys.exit(0)

# Helper Function
def matlab_to_python(data : Any) -> Any:
    """
    Converts common MATLAB data types returned by the engine into JSON-Serializable Python types.
    """
    if isinstance(data, (str, int, float, bool, type(None))):
        # already JSON-serializable
        return data
    elif isinstance(data, matlab.double):
        # convert MATLAB double array to Python list (handles scalars, vectors, matrices)
        # using squeeze to remove singleton dimensions for simpler representation
        np_array = np.array(data).squeeze()
        if np_array.ndim == 0:
            return float(np_array)
        else:
            return np_array.tolist()
    elif isinstance(data, matlab.logical):
        np_array = np.array(data).squeeze()
        if np_array.ndim == 0:
            return bool(np_array)
        else:
            return np_array.tolist()
    elif isinstance(data, matlab.char):
        return str(data)
    else:
        logger.warning(f"Unsupported MATLAB type encountered: {type(data)}. Returning string representation.")
        try:
            return str(data)
        except Exception as e:
            return f"Unserializable MATLAB Type: {type(data)}"
    
    # --- TODO: Add more MATLAB types ---


@mcp.tool()
async def runMatlabCode(code: str) -> dict:
    """
    Run MATLAB code in a shared MATLAB session.
    """
    # Returns a dictionary with status and output/message.
    logger.info(f"Running MATLAB code request: {code[:100]}...")
    # --- Try executing using a temporary file ---
    try:
        temp_filename = "temp_script.m"
        with open(temp_filename, "w") as f:
            f.write(code)
        # Run blocking MATLAB call in a thread
        await asyncio.to_thread(eng.run, temp_filename, nargout=0)
        logger.info("Code executed successfully using temp file method.")
        return {"status": "success", "output": "Code executed successfully via temp file."}

    except matlab.engine.MatlabExecutionError as e_run:
        logger.warning(f"Temp file 'run' method failed: {e_run}. Trying evalc as fallback...")

        # --- Fall back ONLY to evalc ---
        try:
            result = await asyncio.to_thread(eng.evalc, code)
            logger.info("Code executed successfully using evalc fallback method.")
            return {"status": "success", "output": result} 

        except matlab.engine.MatlabExecutionError as e_evalc:
            # If evalc also fails
            logger.error(f"evalc fallback method also failed: {e_evalc}", exc_info=True)
            return {
                "status": "error",
                "error_type": "MatlabExecutionError",
                "stage": "evalc_fallback", # Indicate failure occurred during evalc
                "message": f"Execution failed (tried temp file then evalc): {str(e_evalc)}"
            }
        except Exception as e_evalc_other:
            logger.error(f"Unexpected error during evalc fallback: {e_evalc_other}", exc_info=True)
            return {
                "status": "error",
                "error_type": e_evalc_other.__class__.__name__,
                "stage": "evalc_fallback",
                "message": f"Unexpected error during evalc fallback: {str(e_evalc_other)}"
            }

    except matlab.engine.EngineError as e_eng:
        logger.error(f"MATLAB Engine communication error: {e_eng}", exc_info=True)
        return {
            "status": "error",
            "error_type": "EngineError",
            "message": f"MATLAB Engine error: {str(e_eng)}"
        }
    except Exception as e_outer:
        logger.error(f"Unexpected error executing MATLAB code: {e_outer}", exc_info=True)
        return {
            "status": "error",
            "error_type": e_outer.__class__.__name__,
            "message": f"Unexpected error: {str(e_outer)}"
        }

@mcp.tool()
async def getVariable(variable_name: str) -> dict:
    """
    Gets the value of a variable from the MATLAB workspace.

    Args:
        variable_name: The name of the variable to retrieve.

    Returns:
        A dictionary with status and either the variable's value (JSON serializable)
        or an error message, including error_type.
    """
    logger.info(f"Attempting to get variable: '{variable_name}'")
    try:
        if not eng:
            logger.error("No active MATLAB session found for getVariable.")
            return {"status": "error", "error_type": "RuntimeError", "message": "No active MATLAB session found."}

        # using asyncio.to_thread for the potentially blocking workspace access
        # directly accessing eng.workspace[variable_name] is blocking
        def get_var_sync():
             if variable_name not in eng.workspace:
                 raise KeyError(f"Variable '{variable_name}' not found in MATLAB workspace.")
             return eng.workspace[variable_name]

        matlab_value = await asyncio.to_thread(get_var_sync)

        # convert matlab value to a JSON-serializable Python type
        python_value = matlab_to_python(matlab_value)

        # test serialization before returning
        try:
            json.dumps({"value": python_value}) # test within dummy "dict"
            logger.info(f"Successfully retrieved and converted variable '{variable_name}'.")
            return {"status": "success", "variable": variable_name, "value": python_value}
        except TypeError as json_err:
            logger.error(f"Failed to serialize MATLAB value for '{variable_name}' after conversion: {json_err}", exc_info=True)
            return {
                "status": "error",
                "error_type": "TypeError",
                "message": f"Could not serialize value for variable '{variable_name}'. Original MATLAB type: {type(matlab_value)}"
            }

    except KeyError as ke:
        logger.warning(f"Variable '{variable_name}' not found in workspace: {ke}")
        return {"status": "error", "error_type": "KeyError", "message": str(ke)}
    except matlab.engine.EngineError as e_eng:
        logger.error(f"MATLAB Engine communication error during getVariable: {e_eng}", exc_info=True)
        return {"status": "error", "error_type": "EngineError", "message": f"MATLAB Engine error: {str(e_eng)}"}
    except Exception as e:
        logger.error(f"Unexpected error getting variable '{variable_name}': {e}", exc_info=True)
        return {
            "status": "error",
            "error_type": e.__class__.__name__,
            "message": f"Failed to get variable '{variable_name}': {str(e)}"
        }

if __name__ == "__main__":
    logger.info("Starting MATLAB MCP server...")
    mcp.run(transport='stdio')
    logger.info("MATLAB MCP server is running...")