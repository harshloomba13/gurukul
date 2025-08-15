#!/usr/bin/env python3
"""
Automation script for generating web apps from Figma mockups using Claude Code CLI.
This script automates the process that was previously done manually through Claude Code.
"""

import subprocess
import sys
import time
import os
import random
from typing import Optional, List, Dict
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout)
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if datetime.now() - self.last_failure_time < self.timeout:
                raise Exception(f"Circuit breaker OPEN: Service unavailable for {self.timeout.seconds}s")
            else:
                self.state = "HALF_OPEN"
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            print(f"Circuit breaker OPEN: {self.failure_count} failures detected")

class ClaudeCodeAutomation:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.claude_circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=120)
        self.ensure_project_directory()
    
    def ensure_project_directory(self):
        """Ensure we're in the correct project directory."""
        if not os.path.exists(self.project_path):
            raise Exception(f"Project directory does not exist: {self.project_path}")
        os.chdir(self.project_path)
        print(f"Working in directory: {os.getcwd()}")
    
    def _run_claude_subprocess(self, prompt: str, timeout: int = 300) -> bool:
        """Internal method to run Claude subprocess."""
        result = subprocess.run(
            ["claude", "code", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=self.project_path
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        if result.returncode != 0:
            raise Exception(f"Claude command failed with return code {result.returncode}")
        
        return True

    def run_claude_command(self, prompt: str, timeout: int = 300, max_retries: int = 3) -> bool:
        """
        Execute a Claude Code command with circuit breaker and exponential backoff retry logic.
        Returns True if successful, False otherwise.
        """
        for attempt in range(max_retries):
            try:
                print(f"\n{'='*60}")
                print(f"Executing Claude Code command (attempt {attempt + 1}/{max_retries}):")
                print(f"Circuit breaker state: {self.claude_circuit_breaker.state}")
                print(f"Prompt: {prompt[:100]}...")
                print(f"{'='*60}")
                
                # Use circuit breaker to execute command
                self.claude_circuit_breaker.call(self._run_claude_subprocess, prompt, timeout)
                return True
                
            except subprocess.TimeoutExpired:
                print(f"Command timed out after {timeout} seconds")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    return False
            except Exception as e:
                error_msg = str(e)
                print(f"Error running Claude command: {error_msg}")
                
                # If circuit breaker is open, don't retry
                if "Circuit breaker OPEN" in error_msg:
                    print("Service temporarily unavailable due to circuit breaker")
                    return False
                
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    return False
        
        print(f"All {max_retries} attempts failed")
        return False
    
    def generate_app_from_figma(self, figma_url: str) -> bool:
        """Generate a single-page app from one Figma URL."""
        return self.generate_multi_page_app([{"url": figma_url, "name": "home", "route": "/"}])
    
    def generate_multi_page_app(self, figma_pages: List[Dict[str, str]]) -> bool:
        """
        Complete automation flow for generating a multi-page web app from multiple Figma mockups.
        
        Args:
            figma_pages: List of dicts with 'url', 'name', and 'route' keys
                       e.g., [{'url': 'figma_url_1', 'name': 'home', 'route': '/'},
                             {'url': 'figma_url_2', 'name': 'about', 'route': '/about'}]
        """
        print(f"Starting automated multi-page Figma to web app generation...")
        print(f"Generating {len(figma_pages)} pages: {[p['name'] for p in figma_pages]}")
        
        # Step 0: Clear previous generated files to ensure fresh start
        clear_prompt = """
        IMPORTANT: Before generating the new webapp, you MUST perform a complete cleanup:
        
        1. Delete ALL files in src/app/ EXCEPT layout.tsx and globals.css
        2. Delete the entire .next/ directory if it exists (Next.js build cache)
        3. Delete any public/assets/ or similar asset directories that were auto-generated
        4. Clear any component files that were previously generated
        
        Use bash commands to ensure complete cleanup:
        - rm -rf .next/
        - rm -rf src/app/page.tsx src/app/*/
        - rm -rf public/assets/ (if it exists and contains auto-generated assets)
        
        This is critical to ensure each new Figma mockup generates a completely fresh webapp without any interference from previous generations. Do NOT skip this step.
        """
        
        success = self.run_claude_command(clear_prompt)
        if not success:
            print("Step 0 failed: Cleanup of previous files")
            return False
        
        print("✅ Step 0 completed: Previous files cleaned up")
        
        # Step 1: Generate pages from all Figma mockups
        page_details = "\n".join([f"- {page['name']}: {page['url']} (route: {page['route']})" for page in figma_pages])
        
        step1_prompt = f"""
        Create a multi-page Next.js application using these Figma mockups:
        
        {page_details}
        
        CRITICAL Instructions:
        1. FIRST: Use the figma dev MCP server to analyze EACH mockup URL individually and understand what each design contains
        2. Create separate page components for each route using Next.js 13+ app router structure:
           - Home page (/): src/app/page.tsx  
           - Other pages: src/app/[route-name]/page.tsx (e.g., src/app/about/page.tsx for /about)
        3. Each page should be generated from its SPECIFIC Figma URL - do NOT reuse content between pages
        4. Use the recharts library for any charts/data visualization found in the mockups
        5. Ensure consistent styling across all pages using TailwindCSS
        6. Add navigation between pages using Next.js Link components (create a simple nav bar)
        7. After generating all pages, use playwright MCP server to screenshot each page
        8. Verify each generated page matches its corresponding Figma mockup
        
        IMPORTANT: Each Figma URL should produce DIFFERENT content. Do not generate the same page multiple times.
        """
        
        success = self.run_claude_command(step1_prompt)
        if not success:
            print("Step 1 failed: Multi-page Figma analysis and code generation")
            return False
        
        print("✅ Step 1 completed: All Figma mockups analyzed and pages generated")
        
        # Step 2: Run tests and build verification
        step2_prompt = """
        Run the build command to ensure there are no compilation errors. Fix any TypeScript or linting issues that arise. Then start the development server and take screenshots of all pages using Playwright to verify each page matches its corresponding mockup. Test navigation between pages.
        """
        
        success = self.run_claude_command(step2_prompt)
        if not success:
            print("Step 2 failed: Build verification and testing")
            return False
        
        print("✅ Step 2 completed: Multi-page application built and verified")
        
        print("🎉 Multi-page automation completed successfully!")
        return True

def main(figma_url: Optional[str] = None):
    """Main function to run the automation."""
    # Configuration - use provided URL or default
    if figma_url is None:
        figma_url = "https://www.figma.com/design/MewdbgLi2pZnom6efzBGv3/Untitled?node-id=1-649&t=252vkstW8GfKizQG-11"
    
    project_path = "/Users/harshloomba/Documents/gurukul/playground/figma_to_webapp"
    
    try:
        # Initialize automation
        automation = ClaudeCodeAutomation(project_path)
        
        # Run the automation
        success = automation.generate_app_from_figma(figma_url)
        
        if success:
            print("\n🎉 Automation completed successfully!")
            print("Your Next.js application has been generated from the Figma mockup.")
            print(f"Project location: {project_path}")
            print("Run 'npm run dev' to start the development server.")
        else:
            print("\n❌ Automation failed. Please check the logs above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Automation error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
