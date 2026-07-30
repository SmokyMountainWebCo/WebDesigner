// QA harness for a built one-file page.
//
//   node tools/check.js dist/page.html
//
// Checks: no console/page errors, the WebGL background canvas is still
// displayed (a shader compile error hides it — otherwise completely silent),
// no unresolved {{TOKENS}}, and reports the sections, headings and outbound
// links it found. Drops three screenshots next to the input file at scroll
// depths 0 / mid / end so you can eyeball the scene's arc.
//
// Requires playwright with a Chromium. If your Chromium lives at a fixed
// path, set CHROMIUM_PATH and this uses it; otherwise Playwright's default
// download is used.
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const input = process.argv[2];
  if (!input) { console.error('usage: node tools/check.js <built.html>'); process.exit(2); }
  const abs = path.resolve(input);
  const dir = path.dirname(abs);
  const stem = path.basename(abs).replace(/\.html?$/i, '');

  const launchOpts = { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] };
  if (process.env.CHROMIUM_PATH) launchOpts.executablePath = process.env.CHROMIUM_PATH;

  const browser = await chromium.launch(launchOpts);
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));

  await page.goto('file://' + abs);
  await page.waitForTimeout(1800);

  const info = await page.evaluate(() => {
    const c = document.getElementById('sky');
    return {
      title: document.title,
      canvasPresent: !!c,
      canvasVisible: c && getComputedStyle(c).display !== 'none',
      sections: [...document.querySelectorAll('section[id], section.frame')].length,
      h2s: [...document.querySelectorAll('h2')].map(h => h.textContent.trim().replace(/\s+/g, ' ')),
      outboundLinks: [...document.querySelectorAll('a[href]')]
        .map(a => a.getAttribute('href')).filter(h => h && !h.startsWith('#')),
      noindex: !!document.querySelector('meta[name="robots"][content*="noindex"]'),
      leftoverTokens: (document.documentElement.outerHTML.match(/\{\{[A-Z0-9_]+\}\}/g) || []),
    };
  });

  await page.screenshot({ path: path.join(dir, stem + '.qa-1-top.png') });
  await page.evaluate(() => scrollTo(0, innerHeight * 3.4));
  await page.waitForTimeout(2200);
  await page.screenshot({ path: path.join(dir, stem + '.qa-2-mid.png') });
  await page.evaluate(() => scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(2200);
  await page.screenshot({ path: path.join(dir, stem + '.qa-3-end.png') });

  await browser.close();

  const problems = [];
  if (!info.canvasVisible) problems.push('background canvas is hidden (shader likely failed to compile, or WebGL unavailable)');
  if (errors.length) problems.push(errors.length + ' console/page error(s)');
  if (info.leftoverTokens.length) problems.push('unresolved tokens: ' + info.leftoverTokens.join(', '));

  console.log(JSON.stringify({ ...info, errors }, null, 1));
  console.log('screenshots:', stem + '.qa-{1-top,2-mid,3-end}.png');
  if (problems.length) { console.error('\nFAIL:\n - ' + problems.join('\n - ')); process.exit(1); }
  console.log('\nPASS');
})().catch(e => { console.error('harness error:', e.message); process.exit(1); });
