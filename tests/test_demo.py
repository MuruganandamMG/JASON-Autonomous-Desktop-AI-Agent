import asyncio
import socket
import sys
import pytest
from jason.shells import Shells
from jason.browser import Browser

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        return s.getsockname()[1]

async def ready(p):
    for _ in range(30):
        try:
            reader,writer=await asyncio.wait_for(asyncio.open_connection('127.0.0.1',p),.3)
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError,TimeoutError): await asyncio.sleep(.05)
    return False

@pytest.mark.timeout(40)
async def test_frontend_diagnostics_backend_selective_stop(tmp_path):
    (tmp_path/'index.html').write_text('<html><title>JASON acceptance</title><body>Demo frontend ready</body></html>')
    front,back=port(),port()
    shells=Shells(tmp_path)
    browser=Browser([f'http://127.0.0.1:{front}'],headless=True)
    python_path=sys.executable.replace("'","''")
    try:
        await shells.run(1,f"& '{python_path}' -m http.server {front} --bind 127.0.0.1",'frontend')
        await shells.run(2,"Write-Output 'Diagnostics verified'",'diagnostics')
        await shells.run(3,f"& '{python_path}' -m http.server {back} --bind 127.0.0.1",'backend')
        assert await ready(front),shells.output(1)
        assert await ready(back),shells.output(3)
        assert await asyncio.to_thread(shells.sessions[2].done.wait,15)
        result=await browser.navigate(f'http://127.0.0.1:{front}')
        assert result['title']=='JASON acceptance'
        assert 'Demo frontend ready' in result['text']
        assert 'Diagnostics verified' in shells.output(2)
        await shells.stop(3)
        assert await ready(front)
        assert shells.sessions[1].process.isalive()
        assert shells.sessions[2].process.isalive()
    finally:
        await browser.close()
        await shells.close()

