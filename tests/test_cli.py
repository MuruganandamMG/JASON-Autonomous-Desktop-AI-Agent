import subprocess
import sys

def test_cli_piped_local_controls_do_not_require_console(tmp_path):
    result=subprocess.run([sys.executable,'-m','jason','--state',str(tmp_path/'.state')],
        input='/tasks\n/exit\n',text=True,capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr
    assert 'JASON' in result.stdout
    assert '[]' in result.stdout

