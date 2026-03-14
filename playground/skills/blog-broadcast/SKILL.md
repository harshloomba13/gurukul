---
name: blog-broadcast
description: Cross-post a blog to Substack (newsletter) and Medium with correct canonical URLs, metadata, and verification checks.
---

# Blog Broadcast (Substack + Medium)

Use this skill when the user wants to cross-post a blog to Substack and Medium, with Substack as the primary newsletter destination and Medium as a secondary distribution channel.

## Quick start (ask for these)
- Source content: markdown or a paste of the article body.
- Primary URL choice (default: Substack post URL).
- Metadata: title, subtitle/dek, tags, cover image, author/publication.
- Existing Medium or Substack URLs (if already published).

If only a Medium URL is provided and network access is allowed, fetch the content. Otherwise ask the user to paste the article body.

## Workflow

### 1) Prepare the post
- Normalize title, subtitle/dek, and section headings.
- Add a short intro paragraph for Substack readers if needed.
- Add CTAs at the end (newsletter + follow links).
- Decide canonical URL (default: Substack).

### 2) Publish on Substack (primary)
**Default: manual**
- Create a new post in Substack.
- Paste content and upload cover image.
- Set tags/sections.
- If Substack UI provides canonical URL/SEO settings, set canonical to the Substack URL itself (or to the preferred primary if different).
- Publish as a newsletter post (per user preference).

**If the user has an API token**
- Substack does not provide a stable official publishing API. Confirm the exact method/endpoint before automating.
- If no official API is available, keep this step manual.

### 3) Publish on Medium (secondary)
**Manual (recommended)**
- Use “Import a story” if a public URL exists, or paste the content.
- Set the canonical URL to the Substack post URL in Medium’s “Advanced settings”.
- Add tags (Medium allows up to 5).
- Publish.

**Medium API (optional)**
If the user provides an integration token and user ID:
- Create the post with `canonicalUrl` set to the Substack URL.
- Example fields: `title`, `contentFormat` (markdown or html), `content`, `canonicalUrl`, `tags`, `publishStatus`.

### 4) Verification
- Confirm both URLs load publicly.
- Ensure Medium displays the canonical link in page source.
- Verify Substack email delivery (if sent as newsletter).
- Provide final summary with both URLs and canonical choice.

## Output format
- Substack URL
- Medium URL
- Canonical URL
- Metadata used (title, tags, cover image)

## Notes
- If the user wants Medium as primary, flip canonical accordingly.
- Keep secrets out of the workspace; never store tokens in plain text.
