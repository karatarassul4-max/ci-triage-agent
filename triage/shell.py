import subprocess


def run(cmd, cwd, timeout=300):
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 99, 'timeout'
    return result.returncode, result.stdout + result.stderr