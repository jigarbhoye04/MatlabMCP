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
async def runMatlabCode(code: str) -> Any:
    """
    Run MATLAB code in a shared MATLAB session.
    """
    logger.info(f"Running MATLAB code request: {code[:100]}...")
    try:
        if not eng:
            raise RuntimeError("No active MATLAB session found.")
        
        # using a temporary file
        try:
            temp_filename = "temp_script.m"
            with open(temp_filename, "w") as f:
                f.write(code)
            
            eng.run(temp_filename, nargout=0)
            logger.info("Code executed successfully using temp file method.")
            return "Code executed successfully"
        except matlab.engine.MatlabExecutionError as e1:
            logger.warning(f"evalc method failed: {e1}")

            # Fall back to using evalc which handles multi-line code better
            try:
                result = eng.evalc(code)
                logger.info("Code executed successfully using evalc")
                return result
            

            except matlab.engine.MatlabExecutionError as e2:
                logger.warning(f"Temp file method failed: {e2}")
                
                # try executing line by line
                logger.info("Trying line-by-line execution...")
                result = None
                code_lines = code.strip().split('\n')
                for line in code_lines:
                    line = line.strip()
                    if line and not line.startswith('%'):  # Skip empty lines and comments
                        result = eng.eval(line, nargout=0)
                
                logger.info("Code executed successfully line by line")
                return "Code executed successfully line by line"
                
    except Exception as e:
        logger.error(f"Error executing MATLAB code: {e}", exc_info=True)
        error_message = str(e)
        return f"Error: {error_message}"
    
if __name__ == "__main__":
    logger.info("Starting MATLAB MCP server...")
    mcp.run(transport='stdio')
    logger.info("MATLAB MCP server is running...")