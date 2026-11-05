from pathlib import Path
import re

plan = Path(__file__).resolve().parents[1] / "PROJECT_PLAN.md"
text = plan.read_text(encoding="utf-8")
rows = re.findall(r"^- \[([ xX])\] \*\*Day \d{2} —", text, flags=re.MULTILINE)
done = sum(x.lower() == "x" for x in rows)
print(f"Completed: {done}/{len(rows)} sessions ({done/len(rows)*100:.1f}%)" if rows else "No tracking rows found")
print(f"Hours completed: {done*2}/{len(rows)*2}")
