import asyncio
import pytest
from jason.shells import Shells

async def test_background_child_prevents_other_owner_reuse(tmp_path):
    s=Shells(tmp_path)
    try:
        await s.run(1,"Start-Process $PSHOME/pwsh.exe -ArgumentList '-NoProfile','-Command','Start-Sleep 30' -WindowStyle Hidden",'first')
        assert await asyncio.to_thread(s.sessions[1].done.wait,15)
        assert s.sessions[1].job.count()>1
        with pytest.raises(ValueError,match='background'):
            await s.run(1,'echo second','second')
        await s.run(2,'Write-Output independent','other')
        assert await asyncio.to_thread(s.sessions[2].done.wait,15)
        await s.stop(1)
        assert s.sessions[2].process.isalive()
    finally:
        await s.close()
