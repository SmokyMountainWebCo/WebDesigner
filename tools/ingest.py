#!/usr/bin/env python3
"""Unpack and inventory a drop folder of saved pages and archives.

  python3 tools/ingest.py intake/ -o _work/

Walks a folder of saved .html files, .zip archives, and loose assets;
safely extracts the archives; hashes and de-duplicates everything; and
writes _work/manifest.json plus a printed summary.

Nothing is analyzed here — that's harvest.py. This step only answers
"what did I actually drop in, and where is it now."

Safety, because archives from anywhere are hostile input:
  - path traversal (zip-slip) entries are refused, not sanitized
  - absolute paths and symlink entries are refused
  - a compression-ratio ceiling stops zip bombs (--max-ratio)
  - a per-archive uncompressed ceiling stops slow bombs (--max-bytes)
Refusals are reported and the rest of the archive still extracts.

Stdlib only.
"""
import argparse, hashlib, json, os, shutil, stat, sys, zipfile
from datetime import datetime, timezone

# What we care about, by extension. Everything else is recorded as "other"
# so nothing silently disappears from the inventory.
KINDS = {
    "page":    {".html", ".htm", ".xhtml"},
    "style":   {".css"},
    "script":  {".js", ".mjs", ".ts", ".jsx", ".tsx"},
    "font":    {".woff2", ".woff", ".ttf", ".otf", ".eot"},
    "image":   {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg", ".ico", ".bmp", ".tiff"},
    "video":   {".mp4", ".webm", ".mov", ".m4v"},
    "doc":     {".md", ".txt", ".pdf", ".rtf", ".docx"},
    "data":    {".json", ".csv", ".tsv", ".xml", ".yml", ".yaml", ".geojson"},
    "archive": {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z"},
}
EXT_KIND = {ext: kind for kind, exts in KINDS.items() for ext in exts}

# Saved-page sidecar folders ("Page Title_files/") and OS/tool noise.
NOISE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", "__MACOSX"}


def kind_of(path):
    return EXT_KIND.get(os.path.splitext(path)[1].lower(), "other")


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def safe_extract(zpath, dest, max_ratio, max_bytes, log):
    """Extract a zip, refusing hostile entries. Returns (extracted, refused)."""
    extracted, refused, total_out = [], [], 0
    try:
        zf = zipfile.ZipFile(zpath)
    except (zipfile.BadZipFile, OSError) as e:
        log.append("REFUSED archive %s: unreadable (%s)" % (zpath, e))
        return extracted, [("<archive>", "unreadable: %s" % e)]

    with zf:
        for info in zf.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            # Symlinks and special files. The file-type bits live in the top
            # half of external_attr — but plenty of zip writers (including
            # Python's own writestr) record permission bits and leave the type
            # bits at zero. Only judge the type when it was actually recorded,
            # or every such archive gets refused wholesale.
            mode = info.external_attr >> 16
            if mode & 0o170000 and not stat.S_ISREG(mode):
                kindname = "symlink" if stat.S_ISLNK(mode) else "not a regular file"
                refused.append((name, kindname))
                continue
            if os.path.isabs(name) or name.startswith(("/", "\\")) or ".." in name.replace("\\", "/").split("/"):
                refused.append((name, "path traversal or absolute path"))
                continue
            if any(part in NOISE_NAMES for part in name.replace("\\", "/").split("/")):
                continue
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > max_ratio and info.file_size > 1 << 20:
                    refused.append((name, "compression ratio %.0f:1 exceeds --max-ratio" % ratio))
                    continue
            if total_out + info.file_size > max_bytes:
                refused.append((name, "archive exceeds --max-bytes uncompressed"))
                continue

            target = os.path.realpath(os.path.join(dest, name))
            if not target.startswith(os.path.realpath(dest) + os.sep):
                refused.append((name, "resolves outside destination"))
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            try:
                with zf.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out, 1 << 20)
            except (OSError, zipfile.BadZipFile, RuntimeError) as e:
                refused.append((name, "extract failed: %s" % e))
                continue
            total_out += info.file_size
            extracted.append(target)

    for name, why in refused:
        log.append("REFUSED %s :: %s — %s" % (os.path.basename(zpath), name, why))
    return extracted, refused


def main():
    ap = argparse.ArgumentParser(description="Unpack and inventory a drop folder.")
    ap.add_argument("source", help="folder of saved pages / zips (e.g. intake/)")
    ap.add_argument("-o", "--out", default="_work", help="work folder (default: _work)")
    ap.add_argument("--max-ratio", type=float, default=200.0, help="max compression ratio per entry (default 200)")
    ap.add_argument("--max-bytes", type=float, default=2e9, help="max uncompressed bytes per archive (default 2GB)")
    ap.add_argument("--keep", action="store_true", help="keep any previous unpacked output")
    args = ap.parse_args()

    if not os.path.isdir(args.source):
        sys.exit("error: %s is not a folder" % args.source)

    unpacked = os.path.join(args.out, "unpacked")
    if os.path.isdir(unpacked) and not args.keep:
        shutil.rmtree(unpacked)
    os.makedirs(unpacked, exist_ok=True)

    log, records, archives = [], [], 0

    # Pass 1 — archives, extracted into _work/unpacked/<stem>/
    for root, dirs, files in os.walk(args.source):
        dirs[:] = [d for d in dirs if d not in NOISE_NAMES]
        for fn in sorted(files):
            if fn in NOISE_NAMES:
                continue
            path = os.path.join(root, fn)
            if kind_of(fn) != "archive":
                continue
            if not fn.lower().endswith(".zip"):
                log.append("SKIPPED %s: only .zip is unpacked (extract it by hand first)" % path)
                continue
            archives += 1
            stem = os.path.splitext(fn)[0]
            dest = os.path.join(unpacked, stem)
            os.makedirs(dest, exist_ok=True)
            got, _ = safe_extract(path, dest, args.max_ratio, args.max_bytes, log)
            for p in got:
                records.append({"path": p, "from_archive": os.path.relpath(path, args.source)})

    # Pass 2 — loose files in the drop folder
    for root, dirs, files in os.walk(args.source):
        dirs[:] = [d for d in dirs if d not in NOISE_NAMES]
        for fn in sorted(files):
            if fn in NOISE_NAMES or kind_of(fn) == "archive":
                continue
            records.append({"path": os.path.join(root, fn), "from_archive": None})

    # Hash, classify, de-duplicate by content
    seen, items, dupes = {}, [], 0
    for rec in records:
        p = rec["path"]
        try:
            size = os.path.getsize(p)
            digest = sha256(p)
        except OSError as e:
            log.append("UNREADABLE %s: %s" % (p, e))
            continue
        if digest in seen:
            dupes += 1
            seen[digest]["duplicates"].append(os.path.relpath(p))
            continue
        item = {
            "path": os.path.relpath(p),
            "kind": kind_of(p),
            "bytes": size,
            "sha256": digest,
            "from_archive": rec["from_archive"],
            "mtime": datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).isoformat(timespec="seconds"),
            "duplicates": [],
            # Provenance is the harvest gate — see docs/INTAKE.md. Nothing
            # graduates into library/ until these two are filled in by hand.
            "source_url": None,
            "license": None,
        }
        seen[digest] = item
        items.append(item)

    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": os.path.abspath(args.source),
        "archives_unpacked": archives,
        "files": len(items),
        "duplicates_collapsed": dupes,
        "bytes": sum(i["bytes"] for i in items),
        "notices": log,
        "items": items,
    }
    os.makedirs(args.out, exist_ok=True)
    mpath = os.path.join(args.out, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)

    by_kind = {}
    for i in items:
        agg = by_kind.setdefault(i["kind"], [0, 0])
        agg[0] += 1
        agg[1] += i["bytes"]

    def mb(n):
        return "%.1f MB" % (n / 1e6) if n >= 1e6 else "%.0f KB" % (n / 1e3)

    print("ingested from %s" % args.source)
    print("  archives unpacked   %d" % archives)
    print("  unique files        %d  (%s)" % (len(items), mb(manifest["bytes"])))
    print("  duplicates collapsed %d" % dupes)
    print()
    print("  %-9s %6s  %10s" % ("kind", "count", "bytes"))
    for kind, (n, b) in sorted(by_kind.items(), key=lambda kv: -kv[1][1]):
        print("  %-9s %6d  %10s" % (kind, n, mb(b)))
    if log:
        print("\n  %d notice(s):" % len(log))
        for line in log[:12]:
            print("   - " + line)
        if len(log) > 12:
            print("   … %d more in manifest.json" % (len(log) - 12))
    print("\nwrote %s" % mpath)
    pages = by_kind.get("page", [0])[0]
    if pages:
        print("next: python3 tools/harvest.py %s -o %s/harvest" % (mpath, args.out))
    else:
        print("next: no pages found — check the drop folder")


if __name__ == "__main__":
    main()
