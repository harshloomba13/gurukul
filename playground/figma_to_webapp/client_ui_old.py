import streamlit as st
from claude_call import ClaudeCodeAutomation

st.set_page_config(page_title="Figma → Next.js", page_icon="🎨", layout="wide")
st.title("🎨 Figma → Next.js (Claude Code)")

with st.sidebar:
    st.header("Project settings")
    project_path = st.text_input("Project path", value=".", help="Root of your Next.js app")

    st.header("Mode")
    mode = st.radio("Generation mode", ["Multi Page", "Single Page"], index=0)

st.subheader("Figma URLs")

default_home  = "https://www.figma.com/design/MewdbgLi2pZnom6efzBGv3/Untitled?node-id=0-1&p=f&t=XYSJC6VIz6Xqfeiy-11"
default_p1    = "https://www.figma.com/design/MewdbgLi2pZnom6efzBGv3/Untitled?node-id=1-1619&p=f&t=XYSJC6VIz6Xqfeiy-11"
default_p2    = "https://www.figma.com/design/MewdbgLi2pZnom6efzBGv3/Untitled?node-id=12-1793&p=f&t=XYSJC6VIz6Xqfeiy-11"

cols = st.columns(3)
home_url = cols[0].text_input("about (/)", value=default_home, placeholder="https://www.figma.com/design/...")
p1_url   = cols[1].text_input("/page-1", value=default_p1, placeholder="https://www.figma.com/design/...")
p2_url   = cols[2].text_input("/page-2", value=default_p2, placeholder="https://www.figma.com/design/...")

extra = st.expander("Add pages /page-3 … /page-6")
with extra:
    p3_url = st.text_input("/page-3", value="", placeholder="https://www.figma.com/design/...")
    p4_url = st.text_input("/page-4", value="", placeholder="https://www.figma.com/design/...")
    p5_url = st.text_input("/page-5", value="", placeholder="https://www.figma.com/design/...")
    p6_url = st.text_input("/page-6", value="", placeholder="https://www.figma.com/design/...")

def build_pages():
    pages = [
        {"url": home_url, "name": "about",   "route": "/about"},
        {"url": p1_url,   "name": "page-1", "route": "/page-1"},
        {"url": p2_url,   "name": "page-2", "route": "/page-2"},
    ]
    if p3_url.strip(): pages.append({"url": p3_url, "name": "page-3", "route": "/page-3"})
    if p4_url.strip(): pages.append({"url": p4_url, "name": "page-4", "route": "/page-4"})
    if p5_url.strip(): pages.append({"url": p5_url, "name": "page-5", "route": "/page-5"})
    if p6_url.strip(): pages.append({"url": p6_url, "name": "page-6", "route": "/page-6"})
    return [p for p in pages if p["url"].strip()]

if st.button("Generate from Figma", type="primary"):
    figma_pages = build_pages()
    if not figma_pages:
        st.warning("Please provide at least one Figma URL."); st.stop()

    st.info("This cleans only the listed routes, keeps everything else, and regenerates pages.")
    with st.spinner("Calling Claude Code and writing files…"):
        automation = ClaudeCodeAutomation(project_path)
        if mode == "Single Page":
            ok = automation.generate_app_from_figma(figma_pages[0]["url"])
        else:
            ok = automation.generate_multi_page_app(figma_pages)

    if ok:
        st.success(f"Done. Generated pages: {', '.join(p['route'] for p in figma_pages)}")
        st.code("\n".join(f"{p['route']} ← {p['url']}" for p in figma_pages), language="text")
        st.caption("Restart your dev server if it was already running.")
    else:
        st.error("Generation failed. Check your terminal for details (look for ❌ lines)." )

st.markdown("---")
st.write("Notes: Multi Page mode replaces only the specified routes each run. Nav is ensured automatically.")
