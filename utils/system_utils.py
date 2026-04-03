import json
import subprocess
import os
import sys

def load_mappings(filepath: str = 'mappings.json') -> dict:
    with open(filepath, 'r') as f:
        return json.load(f)

def run_cmd(cmd: str, cwd: str = None, env: dict = None, raise_on_error: bool = True) -> str:
    """Executes a shell command, streams output to the terminal, and returns the full output."""
    run_env = os.environ.copy()
    run_env["GIT_TERMINAL_PROMPT"] = "0"
    
    if env:
        run_env.update(env)
        
    print(f"\n[Executing]: {cmd}")
    
    # Popen allows us to read the stream in real-time
    process = subprocess.Popen(
        cmd, 
        shell=True, 
        cwd=cwd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, # Combines stderr and stdout
        text=True, 
        env=run_env,
        bufsize=1 # Line buffered
    )
    
    output_lines = []
    
    # Read output line-by-line as it is generated
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        output_lines.append(line)
        
    process.wait()
    combined_output = "".join(output_lines).strip()

    if process.returncode != 0 and raise_on_error:
        raise Exception(f"Command failed: {cmd}\nReturn Code: {process.returncode}\nError: {combined_output}")
    
    return combined_output