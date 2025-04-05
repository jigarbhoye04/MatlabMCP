from typing import Any
# import httpx
from mcp.server.fastmcp import FastMCP
import sys

import matlab.engine
mcp = FastMCP("MatlabMCP")


print("Finding shared MATLAB sessions...")
names = matlab.engine.find_matlab()
print(f"Found sessions: {names}")

if not names:
    print("No shared MATLAB sessions found.")
    print("Please start MATLAB and run 'matlab.engine.shareEngine' in its Command Window.")
    sys.exit(0)
else:
    session_name = names[0] 
    print(f"Connecting to session: {session_name}")
    try:
        eng = matlab.engine.connect_matlab(session_name)
        print("Successfully connected to shared MATLAB session.")
    except matlab.engine.EngineError as e:
        print(f"Error connecting or communicating with MATLAB: {e}")
        sys.exit(0)


@mcp.tool()
async def runMatlabCode(code: str) -> Any:
    """
    Run MATLAB code in a shared MATLAB session.
    """
    print("Running MATLAB code...")
    try:
        if not eng:
            raise RuntimeError("No active MATLAB session found.")
        
        # using a temporary file
        try:
            temp_filename = "temp_script.m"
            with open(temp_filename, "w") as f:
                f.write(code)
            
            eng.run(temp_filename, nargout=0)
            print("Code executed successfully using temp file")
            return "Code executed successfully"
        except matlab.engine.MatlabExecutionError as e1:
            print(f"evalc method failed: {e1}")

            # Fall back to using evalc which handles multi-line code better
            try:
                result = eng.evalc(code)
                print("Code executed successfully using evalc")
                return result
            

            except matlab.engine.MatlabExecutionError as e2:
                print(f"Temp file method failed: {e2}")
                
                # try executing line by line
                print("Trying line-by-line execution...")
                result = None
                code_lines = code.strip().split('\n')
                for line in code_lines:
                    line = line.strip()
                    if line and not line.startswith('%'):  # Skip empty lines and comments
                        result = eng.eval(line, nargout=0)
                
                print("Code executed successfully line by line")
                return "Code executed successfully line by line"
                
    except Exception as e:
        print(f"Error executing MATLAB code: {e}")
        error_message = str(e)
        return f"Error: {error_message}"
    
if __name__ == "__main__":
    mcp.run(transport='stdio')
    print("MATLAB MCP is running...")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Shutting down MATLAB MCP...")
        mcp.shutdown()
        eng.quit()  
        print("MATLAB session closed.")