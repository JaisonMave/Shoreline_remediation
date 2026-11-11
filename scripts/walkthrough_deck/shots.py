import asyncio, sys
from PIL import Image
from playwright.async_api import async_playwright
W, H = 1600, 6000
async def bbox(pg, loc):
    b = await loc.first.bounding_box(); return b
async def crop(pg, name, top_loc, bottom_loc=None, x0=None, x1=None, pad=16, bottom_pad=16):
    await pg.screenshot(path="/tmp/full.png")
    im = Image.open("/tmp/full.png"); s = im.size[0] / W
    t = await bbox(pg, top_loc); b = await bbox(pg, bottom_loc) if bottom_loc is not None else t
    left = x0 if x0 is not None else 300; right = x1 if x1 is not None else W - 10
    box = (int(left * s), int((t["y"] - pad) * s), int(right * s), int((b["y"] + b["height"] + bottom_pad) * s))
    im.crop(box).save(f"dash_{name}.png"); print(name, box)
async def main(which):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1.25)
        await pg.goto("http://localhost:8599", wait_until="domcontentloaded", timeout=120000)
        await pg.wait_for_selector("text=Cleanup options for this site", timeout=180000)
        await pg.wait_for_timeout(12000)
        main_x = (await bbox(pg, pg.locator("[data-testid='stMain']")))["x"]
        if which == "worked":
            await crop(pg, "open", pg.locator(".hero"), pg.get_by_text("Chosen by a fixed rule"), x0=0, pad=40)
            await crop(pg, "map", pg.locator("[data-testid='stDeckGlJsonChart']"), pg.get_by_text("Salt-marsh edge cells in this basin"), x0=main_x + 40)
            await crop(pg, "expected", pg.get_by_text("Expected marsh-edge loss", exact=True), pg.get_by_text("Expected rate: marsh edge"), x0=main_x + 40)
            await pg.get_by_text("Rule-screening inputs implied by this site").click(); await pg.get_by_text("Limits of this evidence").click(); await pg.wait_for_timeout(2500)
            await crop(pg, "options", pg.get_by_text("Cleanup options for this site", exact=True), pg.get_by_text("Rule screening: existing FAST-like"), x0=main_x + 40)
            await crop(pg, "expanders", pg.get_by_text("Rule-screening inputs implied by this site"), pg.get_by_text("Scope codes for every cell"), x0=main_x + 40)
            await crop(pg, "oil", pg.get_by_text("Search NOAA ADIOS oils"), pg.get_by_text("Source: NOAA ADIOS oil database"), x0=0, x1=main_x, pad=24)
        if which == "pick":
            await pg.get_by_text("Pick a Louisiana edge cell").click(); await pg.wait_for_timeout(8000)
            await crop(pg, "pick", pg.get_by_text("Pick a Louisiana edge cell"), pg.get_by_text("Salt-marsh edge cells in this basin"), x0=main_x + 40)
            await pg.locator("[data-testid='stMain'] [data-testid='stSelectbox']").first.click(); await pg.wait_for_timeout(1500)
            await pg.get_by_role("option", name="Birdfoot").click(); await pg.wait_for_timeout(6000)
            await pg.locator("[data-testid='stCheckbox']").filter(has_text="In-scope cells only").locator('label').click(); await pg.wait_for_timeout(9000)
            await crop(pg, "out", pg.get_by_text("Pick a Louisiana edge cell"), pg.get_by_text("No prediction: the site"), x0=main_x + 40, bottom_pad=24)
        if which == "new":
            await pg.get_by_text("New site (enter values)").click(); await pg.wait_for_timeout(6000)
            inp = pg.get_by_label("Pre-spill edge-loss trend 1999-2008 (m/yr, Landsat)")
            await inp.fill("9"); await inp.press("Enter"); await pg.wait_for_timeout(9000)
            await crop(pg, "new", pg.get_by_text("New site (enter values)"), pg.get_by_text("Expected rate", exact=True), x0=main_x + 40, bottom_pad=90)
        if which == "scenario":
            await pg.get_by_role("tab", name="Scenario screening (rules and synthetic data)").click(); await pg.wait_for_timeout(4000)
            await crop(pg, "scen_before", pg.locator(".hero"), pg.get_by_text("What you will see"), x0=0, pad=40, bottom_pad=60)
            await pg.get_by_role("button", name="Run scenario analysis").click()
            await pg.wait_for_selector("text=Recommendation", timeout=180000); await pg.wait_for_timeout(15000)
            await crop(pg, "scen_after", pg.get_by_text("This view ranks options with FAST-like rules"), pg.get_by_text("How to read uncertainty"), x0=main_x + 40, bottom_pad=60)
            await crop(pg, "scen_plots", pg.get_by_text("Scientific result plots"), pg.get_by_text("Impact and recovery trajectories"), x0=main_x + 40, bottom_pad=700)
            await pg.get_by_role("tab", name="Method test (synthetic data)").click(); await pg.wait_for_timeout(5000)
            await crop(pg, "method", pg.get_by_text("Method test on synthetic data (not evidence)"), pg.get_by_text("Every model below was trained"), x0=main_x + 40, bottom_pad=500)
        await br.close()
asyncio.run(main(sys.argv[1]))
