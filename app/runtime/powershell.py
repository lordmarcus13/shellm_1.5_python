from __future__ import annotations
import asyncio
import psutil
import base64
from typing import Tuple

# SECURITY/RUNTIME FIX: Standardize I/O to UTF-8, abandoning locale dependence
ENCODING = "utf-8"

async def run_powershell(cmd: str, timeout_sec: int = 120, elevated: bool = False) -> Tuple[int, str, str]:
    """
    Executes a PowerShell command securely.
    
    SECURITY FIX: 
    - Uses Base64 encoding for the command payload to prevent injection vulnerabilities.
    - Enforces UTF-8 output encoding within the shell session.
    """
    
    # Prepend UTF-8 console encoding directive to ensure we capture special chars correctly
    utf8_preamble = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    full_cmd = utf8_preamble + cmd
    
    # Encode the command to Base64 (UTF-16LE required for PowerShell -EncodedCommand)
    # This neutralizes string escaping/injection attacks.
    b64_cmd = base64.b64encode(full_cmd.encode("utf-16le")).decode("ascii")

    if elevated:
        # Construct the elevation wrapper using the encoded command
        # Note: Capturing output from a RunAs process is essentially impossible without 
        # complex IPC or temporary files because it spawns a new window/process context.
        # This implementation focuses on safe execution.
        ps_args = [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-Command",
            f"Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', '{b64_cmd}' -Wait"
        ]
    else:
        ps_args = [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", b64_cmd
        ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *ps_args, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        pid = proc.pid
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            code = await proc.wait()
            # Decode using strict UTF-8 as enforced in the preamble
            return code, stdout.decode(ENCODING, errors="replace"), stderr.decode(ENCODING, errors="replace")
        except asyncio.TimeoutError:
            _kill_process_tree(pid)
            return 124, "", f"Timed out after {timeout_sec}s"
            
    except Exception as e:
        return 1, "", str(e)

def _kill_process_tree(pid: int):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass