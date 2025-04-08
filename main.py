from typing import Any
from mcp.server.fastmcp import FastMCP
import sys
import logging

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


@mcp.tool()
async def runMatlabCode(code: str) -> dict:
    """
    Run MATLAB code in a shared MATLAB session.
    """
    # Returns a dictionary with status and output/message.
    logger.info(f"Running MATLAB code request: {code[:100]}...")
    try:
        if not eng:
            logger.error("No active MATLAB session found during tool execution.")
            return {"status": "error", "message": "No active MATLAB session found."}

        # --- Try executing using a temporary file ---
        try:
            temp_filename = "temp_script.m"
            with open(temp_filename, "w") as f:
                f.write(code)

            eng.run(temp_filename, nargout=0) # nargout=0 suppresses output to Python
            logger.info("Code executed successfully using temp file method.")
            return {"status": "success", "output": "Code executed successfully via temp file."}

        except matlab.engine.MatlabExecutionError as e_run:
            logger.warning(f"Temp file 'run' method failed: {e_run}. Trying evalc...")

            # --- Fall back to using evalc (captures output) ---
            try:
                result = eng.evalc(code)
                logger.info("Code executed successfully using evalc method.")
                return {"status": "success", "output": result}

            except matlab.engine.MatlabExecutionError as e_evalc:
                logger.warning(f"evalc method failed: {e_evalc}. Trying line-by-line...")

                # --- Fall back to line-by-line execution ---
                try:
                    logger.info("Trying line-by-line execution as final fallback...")
                    code_lines = code.strip().split('\n')
                    last_result = None # Keep track if needed, but output isn't captured
                    for line in code_lines:
                        line = line.strip()
                        if line and not line.startswith('%'):  
                            # nargout=0 suppresses output assignment to last_result from MATLAB
                            eng.eval(line, nargout=0)

                    logger.info("Code executed successfully using line-by-line method.")
                    return {"status": "success", "output": "Code executed successfully line by line."}

                except matlab.engine.MatlabExecutionError as e_line:
                     logger.error(f"Line-by-line execution failed: {e_line}", exc_info=True)
                     return {"status": "error", "message": f"Line-by-line execution failed: {str(e_line)}"}
                except Exception as e_inner_final:
                     logger.error(f"Unexpected error during line-by-line execution: {e_inner_final}", exc_info=True)
                     return {"status": "error", "message": f"Unexpected error during line-by-line: {str(e_inner_final)}"}


    except matlab.engine.EngineError as e_eng:
        logger.error(f"MATLAB Engine communication error: {e_eng}", exc_info=True)
        return {"status": "error", "message": f"MATLAB Engine error: {str(e_eng)}"}

    except Exception as e_outer:
        # any other unexpected errors (file IO, etc.)
        logger.error(f"Unexpected error executing MATLAB code: {e_outer}", exc_info=True)
        error_message = str(e_outer)
        return {"status": "error", "message": error_message}
    
if __name__ == "__main__":
    logger.info("Starting MATLAB MCP server...")
    mcp.run(transport='stdio')
    logger.info("MATLAB MCP server is running...")