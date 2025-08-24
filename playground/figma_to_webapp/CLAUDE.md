# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Figma-to-Next.js automation tool that converts Figma designs into working Next.js applications. The project combines Python automation scripts with a Next.js frontend to generate web applications from Figma prototypes.

## High Level Design (HLD)

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │  Claude CLI API  │    │   Next.js App   │
│  (client_ui.py) │◄──►│ (claude_call.py) │◄──►│   (src/app/)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌────────▼────────┐              │
         │              │  Figma URLs     │              │
         │              │  Route Mapping  │              │
         │              │  JSON Parsing   │              │
         └──────────────┤  File Generation├──────────────┘
                        │  Header Tracking│
                        └─────────────────┘
```

### Data Flow

1. **User Input**: Figma URLs entered via Streamlit interface
2. **URL Processing**: Extract file keys and node IDs from Figma URLs
3. **Prompt Generation**: Build structured prompts for Claude CLI with design requirements
4. **Code Generation**: Claude CLI generates React components based on Figma designs
5. **JSON Parsing**: Strict parsing of Claude output into file objects
6. **File Writing**: Generated pages written to Next.js app structure
7. **Header Injection**: Tracking headers added to identify generated files
8. **Navigation Update**: Nav component automatically generated/updated
9. **Build Verification**: npm build validates generated code

### Core Components

- **claude_call.py**: Main automation engine that interfaces with Claude CLI to generate Next.js code from Figma URLs
- **client_ui.py**: Streamlit web interface for configuring and running the Figma-to-Next.js generation
- **src/app/**: Next.js 15 app router application with generated pages

### Key Architecture Features

- **No-delete safety**: The system never deletes files by default, only overwrites generated files
- **Header-based tracking**: Generated pages are marked with special headers containing Figma metadata
- **Prune functionality**: Can selectively remove only previously generated pages (identified by headers)
- **Navigation auto-generation**: Automatically creates and updates navigation components
- **Atomic operations**: File generation is atomic - either all files succeed or none are written
- **PATH resolution**: Intelligent binary resolution for claude, npm, node across different environments

## Commands

### Development
```bash
npm run dev          # Start Next.js development server with Turbopack
npm run build        # Build the Next.js application
npm run start        # Start production server
npm run lint         # Run ESLint
```

### Python Interface
```bash
python client_ui.py  # Launch Streamlit interface for Figma generation
```

### Testing
No specific test framework is configured. Verify functionality by:
1. Running the build command after generation
2. Checking generated pages load correctly
3. Validating navigation components work

## Generation Process

1. **Input**: Figma URLs with optional route mappings
2. **Processing**: Claude CLI generates React components based on Figma designs
3. **Output**: Next.js pages with proper routing and navigation
4. **Header marking**: Each generated file gets a header with Figma metadata for tracking

### Generated File Headers
All generated pages start with:
```typescript
// GENERATED_FROM_FIGMA_KEY: <FILE_KEY> NODE_ID: <NODE_ID> ROUTE: <ROUTE>
```

## Project Structure

- `/src/app/`: Next.js app router pages and components
- `/src/app/_components/Nav.tsx`: Auto-generated navigation component
- `claude_call.py`: Core automation logic
- `client_ui.py`: Streamlit UI for configuration

## Dependencies

### Next.js Stack
- Next.js 15 with App Router
- React 19
- TypeScript 5
- Tailwind CSS 4
- Recharts for data visualization

### Python Stack
- Streamlit for web interface
- Subprocess handling for Claude CLI integration

## Important Notes

- Generated pages use Tailwind CSS for styling
- Charts are implemented using Recharts with placeholder data
- The system maintains strict JSON parsing for Claude output
- PATH resolution handles common installation locations for required binaries (claude, npm, node)
- Layout.tsx is automatically patched to include navigation component