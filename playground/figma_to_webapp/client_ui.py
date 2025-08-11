import streamlit as st
import os
import time
from claude_call import ClaudeCodeAutomation

# Configure Streamlit page
st.set_page_config(
    page_title="Figma to Next.js Automation",
    page_icon="🎨",
    layout="wide"
)

st.title('🎨 Figma to Next.js Automation with Claude MCP')
st.markdown("Transform your Figma mockups into fully functional Next.js applications!")

# Configuration section
with st.expander("⚙️ Configuration", expanded=False):
    project_path = st.text_input(
        "Project Path", 
        value="/Users/harshloomba/Documents/gurukul/playground/figma_to_webapp",
        help="The local directory where the Next.js app will be generated"
    )

# Mode selection
st.subheader("🎯 Generation Mode")
mode = st.radio(
    "Choose generation mode:",
    ["Single Page", "Multi-Page Website"],
    help="Single Page: One Figma mockup → One page app\nMulti-Page: Multiple Figma mockups → Multi-page website"
)

if mode == "Single Page":
    # Single page input
    st.subheader("📎 Figma Mockup URL")
    figma_link = st.text_input(
        'Enter Figma Mockup Link',
        placeholder="https://www.figma.com/design/...",
        help="Paste the Figma design URL here"
    )
    
    # Example URL for convenience
    st.markdown("**Example URL:**")
    st.code("https://www.figma.com/design/qBmHxaXaI9lKs673rhwAnv/Harsh-Loomba-s-team-library?node-id=3320-92&t=dAC3WES4L2GjthyN-11")
    
    figma_pages = [{"url": figma_link, "name": "home", "route": "/"}] if figma_link else []

else:
    # Multi-page input
    st.subheader("📚 Multiple Figma Mockups")
    st.markdown("Add multiple Figma URLs to create a multi-page website:")
    
    # Initialize session state for pages
    if 'figma_pages' not in st.session_state:
        st.session_state.figma_pages = [{"url": "", "name": "home", "route": "/"}]
    
    figma_pages = []
    
    for i, page in enumerate(st.session_state.figma_pages):
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                url = st.text_input(
                    f"Figma URL {i+1}",
                    value=page["url"],
                    placeholder="https://www.figma.com/design/...",
                    key=f"url_{i}"
                )
            
            with col2:
                name = st.text_input(
                    f"Page Name {i+1}",
                    value=page["name"],
                    placeholder="home",
                    key=f"name_{i}"
                )
            
            with col3:
                route = st.text_input(
                    f"Route {i+1}",
                    value=page["route"],
                    placeholder="/",
                    key=f"route_{i}"
                )
            
            with col4:
                if st.button(f"Remove {i+1}", key=f"remove_{i}") and len(st.session_state.figma_pages) > 1:
                    st.session_state.figma_pages.pop(i)
                    st.rerun()
            
            if url:  # Only add to figma_pages if URL is provided
                figma_pages.append({
                    "url": url,
                    "name": name or f"page{i+1}",
                    "route": route or f"/page{i+1}"
                })
    
    # Add new page button
    if st.button("➕ Add Another Page"):
        st.session_state.figma_pages.append({
            "url": "",
            "name": f"page{len(st.session_state.figma_pages)+1}",
            "route": f"/page{len(st.session_state.figma_pages)+1}"
        })
        st.rerun()
    
    # Update session state with current values
    for i, page in enumerate(figma_pages):
        if i < len(st.session_state.figma_pages):
            st.session_state.figma_pages[i] = page
    
    # Show preview of pages to be generated
    if figma_pages:
        st.markdown("**Pages to be generated:**")
        for page in figma_pages:
            st.write(f"- **{page['name']}** ({page['route']}) → {page['url'][:50]}...")

# Generation section
st.subheader("🚀 Generate Application")

if st.button('Start Generation', type="primary", use_container_width=True):
    if figma_pages:
        # Validate all URLs
        invalid_urls = [page for page in figma_pages if not page["url"].startswith("https://www.figma.com/")]
        if invalid_urls:
            st.error(f"❌ Please provide valid Figma URLs starting with 'https://www.figma.com/' for: {[page['name'] for page in invalid_urls]}")
        else:
            try:
                # Create progress indicators
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Initialize automation
                status_text.text("🔧 Initializing Claude Code Automation...")
                progress_bar.progress(10)
                
                automation = ClaudeCodeAutomation(project_path)
                
                # Run the automation with progress updates
                status_text.text("🎨 Analyzing Figma mockup and generating code...")
                progress_bar.progress(30)
                
                with st.spinner("Running Claude Code automation..."):
                    if mode == "Single Page":
                        success = automation.generate_app_from_figma(figma_pages[0]["url"])
                    else:
                        success = automation.generate_multi_page_app(figma_pages)
                
                if success:
                    progress_bar.progress(100)
                    status_text.text("✅ Generation completed successfully!")
                    
                    if mode == "Single Page":
                        st.success("🎉 Your Next.js application has been generated successfully!")
                    else:
                        st.success(f"🎉 Your multi-page Next.js application with {len(figma_pages)} pages has been generated successfully!")
                    
                    # Show next steps
                    with st.container():
                        st.subheader("📋 Next Steps")
                        st.markdown(f"""
                        1. **Navigate to project directory:**
                           ```bash
                           cd {project_path}
                           ```
                        
                        2. **Start development server:**
                           ```bash
                           npm run dev
                           ```
                        
                        3. **View your app at:**
                           [http://localhost:3000](http://localhost:3000)
                        """)
                        
                        # Show project structure
                        if os.path.exists(project_path):
                            st.subheader("📁 Generated Files")
                            with st.expander("View project structure", expanded=False):
                                try:
                                    for root, dirs, files in os.walk(project_path):
                                        level = root.replace(project_path, '').count(os.sep)
                                        indent = ' ' * 2 * level
                                        st.text(f"{indent}{os.path.basename(root)}/")
                                        subindent = ' ' * 2 * (level + 1)
                                        for file in files[:10]:  # Limit to first 10 files per directory
                                            st.text(f"{subindent}{file}")
                                except Exception as e:
                                    st.text(f"Could not read project structure: {e}")
                
                else:
                    progress_bar.progress(0)
                    status_text.text("❌ Generation failed")
                    st.error("❌ Generation failed. Please check the Claude Code automation logs.")
                    
            except Exception as e:
                st.error(f"❌ Error during automation: {str(e)}")
                st.markdown("**Troubleshooting tips:**")
                st.markdown("- Ensure Claude Code CLI is installed and configured")
                st.markdown("- Check that the project directory exists and is writable")
                st.markdown("- Verify the Figma URL is accessible")
    else:
        if mode == "Single Page":
            st.warning('⚠️ Please provide a valid Figma mockup link.')
        else:
            st.warning('⚠️ Please add at least one Figma mockup with a valid URL.')

# Footer with information
st.markdown("---")
st.markdown("**How it works:**")
st.markdown("""
1. 🔍 **Analyze**: Claude extracts design elements from your Figma mockup
2. 🛠️ **Generate**: Creates Next.js components with TailwindCSS styling
3. 📊 **Charts**: Integrates Recharts for data visualization components
4. 🧪 **Verify**: Uses Playwright to test the generated application
5. ✅ **Deploy**: Ready-to-run Next.js application
""")
