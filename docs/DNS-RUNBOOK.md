# DNS Runbook — pointing domains without breaking anything

> **Owns:** the operational how-to for domains and DNS — the mental
> model, connecting a domain to a live site, retiring temporary and old
> URLs, and the pre-flight checks that keep a site owner's email alive.
> **Not here:** how DNS works as a system, anycast, TTL propagation and
> encrypted DNS — see `INTERNET-SCIENCE.md`. Redirect strategy and its
> effect on indexing — see `MASTERING-THE-INTERNET.md`.

Written for someone doing this for the first time. The failure modes
here are unusually unforgiving: a wrong move can take a site offline,
and a *specific* wrong move can silently kill its email for days. Read
the pre-flight section before touching anything.

---

## The mental model

Three separate things that get confused constantly:

| Layer | What it is | Where it lives |
|---|---|---|
| **The registrar** | Who the domain was bought from and who says you own it. GoDaddy, Namecheap, Cloudflare, Porkbun. | The account the domain is registered in — **this is the ownership layer** |
| **The nameservers** | Which company's DNS system is *authoritative* — i.e. whose answer the internet trusts for this domain | Set at the registrar |
| **The records** | The actual instructions: "this name → that server" | Managed wherever the nameservers point |

Plain version: DNS is the phone book. Somebody types the domain; DNS
answers with which machine to go talk to. You are editing a phone book
entry.

## The records that matter

| Record | Does what | You'll use it for |
|---|---|---|
| **A** | Name → an IPv4 address | Pointing the bare domain (`example.com`) at a host |
| **AAAA** | Name → an IPv6 address | Same, IPv6 |
| **CNAME** | Name → *another name* | `www.example.com` → `their-site.netlify.app` |
| **MX** | Where email for this domain goes | **Do not touch. See the warning below.** |
| **TXT** | Free-text verification | Domain verification, SPF/DKIM (email authentication) |

**Apex vs subdomain:** the bare domain (`example.com`, called the apex or
root, often shown as `@`) traditionally can't be a CNAME. Subdomains
(`www`, `booking`) can. Modern DNS providers offer ALIAS/ANAME/CNAME
flattening to work around this at the apex — use it if offered.

## ⚠ The one that hurts people: MX records

**If you move nameservers and don't recreate the MX records, email for
that domain stops working.** Not the website — the actual business
email. It fails silently, they don't notice for hours, and mail sent
during that window may bounce permanently.

This is the single most damaging mistake available to you, and it's easy
to make. The pre-flight checklist exists mostly to prevent it.

## Pre-flight — do this every single time

1. **Export or screenshot every existing DNS record before you change
   anything.** All of them, including ones you don't recognize. This is
   the undo button and there isn't another one. Save it somewhere
   durable and dated.
2. **Find out whether email runs on this domain.** Ask plainly: *"Is your
   email address @yourbusiness.com, or is it gmail/yahoo?"* If it's on
   the domain, MX records are live and must survive the move.
3. **Confirm who actually owns the domain** and that you can log into
   the registrar. If a previous developer or a relative owns it, that gets
   resolved *before* anything technical starts.
4. **Lower the TTL to 300 seconds** on the records you'll change, at
   least a few hours (ideally a day) ahead. TTL is how long the internet
   caches the old answer — lowering it first means mistakes take minutes
   to fix instead of a day.
5. **Pick a low-traffic window.** Not Friday afternoon in July.

## Connecting a domain to a live site — the two ways

**Option A — leave nameservers at the registrar, just add records.**
Lower risk, because MX and everything else stay exactly where they are.
Preferred when there is email on the domain.

- `A` record, host `@`, value = the host's IP
- `CNAME` record, host `www`, value = the host's provided hostname

**Option B — move nameservers to the host** (Netlify DNS, Cloudflare,
Vercel). Simpler ongoing management, and required for some features.
But **you must recreate MX and TXT records** in the new provider before
switching, or email dies.

- Copy every existing record into the new provider first
- Only then change the nameservers at the registrar
- Verify email still flows before you walk away

**Get the exact IPs and hostnames from the host's own dashboard at the
time you do it** — do not use values from memory or from this document.
Providers change them, and a stale IP is a dead site.

## Retiring a temporary URL (`something.netlify.app`)

The temp URL doesn't get deleted; it stops being the *public* one.

1. Add the custom domain in the host's dashboard.
2. Set the custom domain as the **primary domain** — the host then
   redirects the temp URL to it automatically.
3. Confirm HTTPS is issued for the new domain before announcing it.
4. Leave the temp URL alive as a redirect. Killing it breaks any link
   anyone saved during the build.

## Migrating from an old site (there was something there before)

**Do not just delete the old site.** Whatever ranking, links, and
bookmarks it accumulated are worth real money.

- **Same domain, new site:** repoint DNS. Old URLs that no longer exist
  should `301` redirect to the closest new page.
- **Different domain entirely:** keep the old domain registered and
  `301` redirect the whole thing to the new one. Do not let it lapse —
  an expired domain with inbound links gets bought by spammers, and it
  will still be carrying the old name.
- **Map the old pages to the new ones** before switching. Anything with
  traffic gets a specific redirect, not a blanket send-to-homepage.

## Verify before you say it's done

- `dig example.com +short` and `dig www.example.com +short` — confirm
  the answers are what you set
- Load the site on cellular data (not your own wifi, which may be
  caching)
- Check HTTPS is valid and not warning
- **If there is email on the domain, send a test message to it and
  confirm it arrives**
- Only then announce that it's live

## When something's wrong

- **Site not resolving:** TTL hasn't expired yet, or the record is on the
  wrong host name (`@` vs `www`). Wait, then re-check.
- **Works at `www` but not the bare domain (or vice versa):** you set one
  record and not the other. Both are needed.
- **HTTPS warning:** the certificate hasn't been issued yet — usually
  resolves within an hour of DNS being correct.
- **HTTPS warning that persists after DNS is correct:** stop waiting and
  read the certificate — `curl -sSv https://the-hostname 2>&1 | grep
  subject:`. A certificate for the platform's own domain
  (`*.theirplatform.com`) rather than the hostname you pointed is not
  slow issuance; it means the platform was never told about the custom
  hostname. A vendor-hosted subdomain has to be registered in the
  vendor's dashboard as well as in DNS — DNS gets the request to the
  right building; the vendor still has to know the name to answer for it
  and issue a certificate. Fix it in their dashboard, not in DNS.
  (Learned on a real cutover; added 2026-08-12.)
- **Email stopped:** MX records didn't survive. Restore from the export
  you took in pre-flight, immediately.

## The habit that makes this safe

Everything above reduces to one thing: **take the export first.** Every
mistake in this document is recoverable in minutes if you have a copy of
what the records looked like before you touched them, and a genuine
emergency if you don't.
