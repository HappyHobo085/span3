import os
import sys
import json
import traceback

sys.path.append(r"C:\Jaco Oosthuizen\Akademia\Derde Jaar (2026)\NSWIW370\Span3_Repo\span3\Backend")
from services.compatibiliteit_service import bereken_voorstad_ooreenstemming, norm_voorstad

with open(os.path.join(os.path.dirname(__file__), "scores_before.json"), "r") as f:
    before = json.load(f)

errors = []
for pair, old_score in before.items():
    a, b = pair.split("|")
    new_score = bereken_voorstad_ooreenstemming(a, b)
    if new_score != old_score:
        errors.append(f"Mismatch for {a} vs {b}: old={old_score}, new={new_score}")

# Ekstra toetse
try:
    assert norm_voorstad("Centurion (Sentraal)") == "centurion sentraal", "norm() failed for hakies"
    assert norm_voorstad("Waterkloof  Glen") == "waterkloof glen", "norm() failed for dubbel spasies"
    assert norm_voorstad("Bailey's Muckleneuk") == "baileys muckleneuk", "norm() failed for apostroof"
except AssertionError as e:
    errors.append(str(e))

if errors:
    print("REGRESSION TEST FAILED:")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print("REGRESSION TEST PASSED!")
