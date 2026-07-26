"""Checks the PDF delivery path in bot.py without touching Telegram.

send_guide() has three sources (cached file_id -> local folder -> website URL)
and a link fallback. A student who finished the test must never be left with
nothing, so every branch is exercised here with a fake chat object.

    python test_guide.py
"""
import asyncio
import os
import sys

import bot
import testmind_core as core

SITE_GUIDES = "C:/Users/Asus/TestMind-site/guides"

ok_count = fail_count = 0


def ok(cond, msg):
    global ok_count, fail_count
    if cond:
        ok_count += 1
        print("  PASS " + msg)
    else:
        fail_count += 1
        print("  FAIL " + msg)


class FakeDoc:
    def __init__(self, file_id):
        self.file_id = file_id


class FakeMsg:
    def __init__(self, doc_id="FILEID-1"):
        self.doc_id = doc_id
        self.documents = []   # what was passed as `document`
        self.texts = []
        self.fail_document = False

    async def reply_document(self, document, filename=None, caption=None, parse_mode=None):
        if self.fail_document:
            raise RuntimeError("simulated Telegram failure")
        # a real upload reads the handle; record enough to identify the source
        self.documents.append(document if isinstance(document, str) else "FILEHANDLE")
        m = FakeMsg()
        m.document = FakeDoc(self.doc_id)
        return m

    async def reply_text(self, text, **kw):
        self.texts.append(text)


ARCH = core.BY_SLUG["ishonchli-dost"]


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


print("\n== every archetype has a PDF next to the site ==")
missing = [s for s in core.BY_SLUG if not os.path.isfile(os.path.join(SITE_GUIDES, s + ".pdf"))]
ok(len(core.BY_SLUG) == 10, "ten archetypes known to the bot")
ok(not missing, "a PDF exists for each (" + (",".join(missing) or "all 10 present") + ")")

print("\n== local folder is used when TESTMIND_GUIDES is set ==")
bot.guide_file_ids.clear()
bot.GUIDES_DIR = SITE_GUIDES
m = FakeMsg("FILEID-LOCAL")
ok(run(bot.send_guide(m, ARCH)) is True, "reports success")
ok(m.documents == ["FILEHANDLE"], "uploaded the local file, not the URL")
ok(not m.texts, "no fallback link was sent")
ok(bot.guide_file_ids.get("ishonchli-dost") == "FILEID-LOCAL", "file_id cached after first send")

print("\n== the cached file_id is reused, so the PDF uploads only once ==")
m2 = FakeMsg("FILEID-LOCAL")
run(bot.send_guide(m2, ARCH))
ok(m2.documents == ["FILEID-LOCAL"], "second send reuses the file_id")

print("\n== with no local folder it falls back to the website URL ==")
bot.guide_file_ids.clear()
bot.GUIDES_DIR = ""
m3 = FakeMsg()
run(bot.send_guide(m3, ARCH))
ok(m3.documents == [bot.GUIDE_URL % "ishonchli-dost"], "sent the public URL")

print("\n== if delivery fails, the student still gets the link ==")
bot.guide_file_ids.clear()
m4 = FakeMsg()
m4.fail_document = True
ok(run(bot.send_guide(m4, ARCH)) is False, "reports failure honestly")
ok(len(m4.texts) == 1 and "guides/ishonchli-dost.pdf" in m4.texts[0],
   "a working download link was sent instead")
ok("ishonchli-dost" not in bot.guide_file_ids, "nothing cached from a failed send")

print("\n" + ("FAILED %d" % fail_count if fail_count else "ALL %d CHECKS PASSED" % ok_count))
sys.exit(1 if fail_count else 0)
