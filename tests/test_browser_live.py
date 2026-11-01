import asyncio
import pytest
from jason.browser import Browser

async def test_real_browser_local_demo_and_redirect_block():
    async def serve(reader, writer):
        request = await reader.read(4096)
        if b'GET /redirect ' in request:
            response = b'HTTP/1.1 302 Found\r\nLocation: https://private.invalid\r\nContent-Length: 0\r\n\r\n'
        else:
            body = b'<html><title>JASON Demo</title><body><button onclick="this.textContent=\'Verified\'">Check</button></body></html>'
            response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body
        writer.write(response)
        await writer.drain()
        writer.close()
    server=await asyncio.start_server(serve,'127.0.0.1',0)
    port=server.sockets[0].getsockname()[1]
    url=f'http://127.0.0.1:{port}'
    b=Browser([url],headless=True)
    try:
        result=await b.navigate(url)
        assert result['title']=='JASON Demo'
        result=await b.interact('button','Check')
        assert 'Verified' in result['text']
        with pytest.raises(Exception):
            await b.navigate(url+'/redirect')
    finally:
        await b.close()
        server.close()
        await server.wait_closed()
