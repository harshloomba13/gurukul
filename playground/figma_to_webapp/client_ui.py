import streamlit as st
from claude_call import ClaudeCodeAutomation

st.set_page_config(page_title="Figma → Next.js", page_icon="🎨", layout="wide")
st.title("🎨 Figma → Next.js (Claude Code)")

with st.sidebar:
    st.header("Project settings")
    project_path = st.text_input("Project path", value=".", help="Root of your Next.js app (folder with package.json)")
    st.header("Mode")
    mode = st.radio("Generation mode", ["Multi Page", "Single Page"], index=0)

st.subheader("Figma URLs → routes")

cols = st.columns(3)
home_url = cols[0].text_input("Home (/)", value="", placeholder="https://www.figma.com/design/...node-id=0-1")
p1_url   = cols[1].text_input("/page-1", value="", placeholder="https://www.figma.com/design/...node-id=...")
p2_url   = cols[2].text_input("/page-2", value="", placeholder="https://www.figma.com/design/...node-id=...")

with st.expander("More routes"):
    p3_url = st.text_input("/page-3", value="", placeholder="https://www.figma.com/design/...")
    p4_url = st.text_input("/page-4", value="", placeholder="https://www.figma.com/design/...")
    p5_url = st.text_input("/page-5", value="", placeholder="https://www.figma.com/design/...")
    p6_url = st.text_input("/page-6", value="", placeholder="https://www.figma.com/design/...")

def build_pages():
    pages = []
    if home_url.strip(): pages.append({"url": home_url.strip(), "name": "home",   "route": "/"})
    if p1_url.strip():   pages.append({"url": p1_url.strip(),   "name": "page-1", "route": "/page-1"})
    if p2_url.strip():   pages.append({"url": p2_url.strip(),   "name": "page-2", "route": "/page-2"})
    if p3_url.strip():   pages.append({"url": p3_url.strip(),   "name": "page-3", "route": "/page-3"})
    if p4_url.strip():   pages.append({"url": p4_url.strip(),   "name": "page-4", "route": "/page-4"})
    if p5_url.strip():   pages.append({"url": p5_url.strip(),   "name": "page-5", "route": "/page-5"})
    if p6_url.strip():   pages.append({"url": p6_url.strip(),   "name": "page-6", "route": "/page-6"})
    return pages

figma_pages_all = build_pages()

if mode == "Single Page":
    st.markdown("**Single Page** will regenerate one route and prune all other *generated* pages.")
    if not figma_pages_all:
        st.info("Provide at least one Figma URL above.")
    else:
        routes = [p["route"] for p in figma_pages_all]
        choice = st.selectbox("Which route to (re)generate?", routes, index=0)
        archive_instead = st.checkbox("Archive pruned pages instead of deleting", value=False, help="Moves to .generated_archive/")
else:
    prune_multi = st.checkbox("Prune pages not listed in this run", value=False)
    archive_instead = st.checkbox("Archive pruned pages instead of deleting", value=False, help="Moves to .generated_archive/")

if st.button("Generate from Figma", type="primary"):
    if not figma_pages_all:
        st.warning("Please provide at least one Figma URL.")
    else:
        automation = ClaudeCodeAutomation(project_path)

        if mode == "Single Page":
            single = next(p for p in figma_pages_all if p["route"] == choice)
            prune_mode = "archive" if archive_instead else "delete"
            ok = automation.generate_multi_page_app([single], prune_unlisted=True, prune_mode=prune_mode)
            show = [single]
        else:
            prune_mode = "archive" if archive_instead else "delete"
            ok = automation.generate_multi_page_app(figma_pages_all, prune_unlisted=prune_multi, prune_mode=prune_mode)
            show = figma_pages_all

        if ok:
            st.success("Generation complete.")
            st.code("\n".join(f"{p['route']} ← {p['url']}" for p in show), language="text")
            st.caption("If your dev server was already running, restart it to reflect deletions/prunes.")
        else:
            st.error("Generation failed. Check your terminal logs for details.")