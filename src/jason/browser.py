from urllib.parse import urlparse

def origin(url):
    p=urlparse(url)
    if p.scheme not in ("http","https") or p.username or p.password or not p.hostname:
        raise ValueError("Only ordinary HTTP(S) URLs are supported.")
    return f"{p.scheme}://{p.hostname.lower()}" + (f":{p.port}" if p.port else "")

class Browser:
    def __init__(self,origins,channel="msedge",headless=False):
        self.origins={origin(u) for u in origins}
        self.channel,self.headless=channel,headless
        self.page=None
        self.driver=None
        self.context=None
        self.revision=0
        self.authorize_origin=None
    def allowed(self,destination):
        return self.authorize_origin(destination) if self.authorize_origin else destination in self.origins
    async def start(self):
        if self.page: return
        from playwright.async_api import async_playwright
        self.driver=await async_playwright().start()
        from .shells import child_env
        self.browser=await self.driver.chromium.launch(headless=self.headless,channel=self.channel,env=child_env())
        self.context=await self.browser.new_context(accept_downloads=False,service_workers="block")
        async def route(r):
            try: allowed=self.allowed(origin(r.request.url))
            except ValueError: allowed=False
            if r.request.resource_type=="document" and not allowed:
                await r.abort()
            else: await r.continue_()
        await self.context.route("**/*",route)
        self.page=await self.context.new_page()
    async def navigate(self,url):
        if not self.allowed(origin(url)): raise ValueError("Origin not approved.")
        await self.start()
        self.revision+=1
        await self.page.goto(url,wait_until="domcontentloaded",timeout=20000)
        return await self.inspect()
    async def inspect(self):
        if not self.page: raise ValueError("Navigate first.")
        if not self.allowed(origin(self.page.url)): raise ValueError("Redirected outside approved origins.")
        return {"url":self.page.url,"title":await self.page.title(),"text":(await self.page.locator("body").inner_text())[:12000]}
    async def interact(self,role,name,text=None):
        if not self.page: raise ValueError("Navigate first.")
        locator=self.page.get_by_role(role,name=name,exact=True)
        self.revision+=1
        if text is None: await locator.click(timeout=5000)
        else: await locator.fill(text,timeout=5000)
        return await self.inspect()
    async def close(self):
        if self.context: await self.context.close()
        if getattr(self,"browser",None): await self.browser.close()
        if self.driver: await self.driver.stop()

