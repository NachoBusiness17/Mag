from pathlib import Path

p = Path("dashboard/static/app.js")
t = p.read_text(encoding="utf-8")

if 'if (name === "diary") loadDiary()' not in t:
    t = t.replace(
        '  if (name === "ideas") loadIdeas();\n  if (name === "status") loadStatus();',
        '  if (name === "ideas") loadIdeas();\n  if (name === "status") loadStatus();\n  if (name === "diary") loadDiary();',
    )

if 'else if (active === "diary") await loadDiary()' not in t:
    t = t.replace(
        '    else if (active === "ideas") await loadIdeas();\n    else if (active === "status") await loadStatus();',
        '    else if (active === "ideas") await loadIdeas();\n    else if (active === "status") await loadStatus();\n    else if (active === "diary") await loadDiary();',
    )

wire = """
  $("#btnHomeDiary")?.addEventListener("click", () => setTab("diary"));
  $("#btnDiaryReload")?.addEventListener("click", () => loadDiary());
  $("#btnDiaryOldest")?.addEventListener("click", () => {
    diaryNewestFirst = false;
    $("#btnDiaryOldest")?.classList.add("on");
    $("#btnDiaryNewest")?.classList.remove("on");
    if (diaryCache) renderDiaryTimeline(diaryCache);
    else loadDiary();
  });
  $("#btnDiaryNewest")?.addEventListener("click", () => {
    diaryNewestFirst = true;
    $("#btnDiaryNewest")?.classList.add("on");
    $("#btnDiaryOldest")?.classList.remove("on");
    if (diaryCache) renderDiaryTimeline(diaryCache);
    else loadDiary();
  });
  $("#btnDiaryCopy")?.addEventListener("click", async () => {
    const text = diaryStoryText();
    if (!text) {
      toast("Load diary first");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      toast("Diary story copied");
    } catch {
      prompt("Copy diary:", text.slice(0, 4000));
    }
  });
"""

if "btnDiaryReload" not in t:
    needle = '$("#btnHomeIdeas")?.addEventListener("click", () => setTab("ideas"));'
    if needle in t:
        t = t.replace(needle, needle + "\n" + wire, 1)
    else:
        # fall back: before bind() end is hard; append after loadDiary block mark
        t = t.replace("function bind() {", "function bind() {" + wire, 1)

p.write_text(t, encoding="utf-8")
print("diary setTab", 'name === "diary"' in t)
print("refresh", 'active === "diary"' in t)
print("wire", "btnDiaryReload" in t)
print("loadDiary", "async function loadDiary" in t)
