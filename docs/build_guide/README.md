# Build guide sources

Markdown for the six tabs of the Claude Doc **C2C Pipeline Build Guide**
(https://claude.ai/code/artifact/bcab6a99-ab4f-46b6-b772-d7480c8ae393), in tab order.
The doc is the live copy; edit there, then mirror here before re-exporting.

Re-export the PDF (needs a venv with `playwright markdown` and `playwright install chromium`;
on this WSL the nss/nspr libs come from a conda env, see LD_LIBRARY_PATH):

    LD_LIBRARY_PATH=<nsslibs>/lib <venv>/bin/python build.py   # -> "Pipeline & Assignments.pdf"

The claude.ai PDF export drops the tabs and does not render mermaid; that is why this exists.
