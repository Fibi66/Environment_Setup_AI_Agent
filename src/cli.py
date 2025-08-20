#!/usr/bin/env python3
import asyncio
import click
import sys
import os
import getpass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file at startup
load_dotenv()

from .core import Config
from .workflow import create_workflow, State


def get_api_key_from_user():
    """Prompt user for API key if not set"""
    print("\n" + "="*60)
    print("🔑 API KEY REQUIRED")
    print("="*60)
    print("\nThis AI agent requires an LLM API key to function.")
    print("\nSupported providers:")
    print("  1. OpenAI (GPT-4, GPT-3.5)")
    print("  2. Anthropic (Claude)")
    print("\nYou can set it in 3 ways:")
    print("  • Environment variable: export OPENAI_API_KEY=sk-...")
    print("  • .env file: OPENAI_API_KEY=sk-...")
    print("  • Enter it now (will not be saved)")
    print("="*60)
    
    choice = input("\nSelect provider [1=OpenAI, 2=Anthropic, q=quit]: ").strip()
    
    if choice.lower() == 'q':
        print("Exiting...")
        sys.exit(0)
    elif choice == '1':
        api_key = getpass.getpass("Enter your OpenAI API key: ").strip()
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
            os.environ['PROVIDER'] = 'openai'
            return True
    elif choice == '2':
        api_key = getpass.getpass("Enter your Anthropic API key: ").strip()
        if api_key:
            os.environ['ANTHROPIC_API_KEY'] = api_key
            os.environ['PROVIDER'] = 'anthropic'
            return True
    
    return False


def validate_api_key(provider: str, api_key: str) -> bool:
    """Basic validation of API key format"""
    if provider == 'openai':
        return api_key.startswith('sk-') and len(api_key) > 20
    elif provider == 'anthropic':
        return api_key.startswith('sk-ant-') and len(api_key) > 20
    return False


@click.command()
@click.argument('project_path', default='.')
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file path')
@click.option('--mode', '-m', type=click.Choice(['auto', 'interactive', 'dry-run']), default='auto')
@click.option('--no-verify', is_flag=True, help='Skip verification step')
@click.option('--fast', is_flag=True, help='Use fast mode (skip analysis)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--api-key', envvar='OPENAI_API_KEY', help='API key (or set via env var)')
def main(
    project_path: str,
    config: Optional[str],
    mode: str,
    no_verify: bool,
    fast: bool,
    verbose: bool,
    api_key: Optional[str]
):
    """
    SetupAgent AI - Intelligent Environment Setup
    
    Automatically configures development environments using AI.
    
    Requires an API key from OpenAI or Anthropic.
    """
    print("""
╔══════════════════════════════════════╗
║      SetupAgent AI v1.0.0            ║
║   Intelligent Environment Setup       ║
║      Powered by Large Language Models ║
╚══════════════════════════════════════╝
    """)
    
    # Run async main with proper cleanup on Windows
    import platform
    if platform.system() == 'Windows':
        # Windows-specific event loop policy to avoid warnings
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    try:
        asyncio.run(run_setup(
            project_path=project_path,
            config_path=config,
            mode=mode,
            no_verify=no_verify,
            fast=fast,
            verbose=verbose
        ))
    finally:
        # Clean shutdown on Windows
        if platform.system() == 'Windows':
            import gc
            gc.collect()
            asyncio.set_event_loop_policy(None)


async def run_setup(
    project_path: str,
    config_path: Optional[str],
    mode: str,
    no_verify: bool,
    fast: bool,
    verbose: bool
):
    try:
        # Load configuration
        cfg = Config(config_path)
        
        # Check LLM configuration
        llm_config = cfg.get_llm_config('primary')
        
        # If no API key, prompt user
        if not llm_config.api_key:
            print("❌ No API key configured!")
            
            # Try to get from user
            if not get_api_key_from_user():
                print("\n❌ API key is required to use SetupAgent AI")
                print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
                sys.exit(1)
            
            # Reload config with new env vars
            cfg = Config(config_path)
            llm_config = cfg.get_llm_config('primary')
            
            # Validate the key format
            if not validate_api_key(llm_config.provider, llm_config.api_key):
                print(f"\n❌ Invalid API key format for {llm_config.provider}")
                sys.exit(1)
        
        print(f"✅ Using {llm_config.provider.upper()} with model: {llm_config.model}")
        
        # Create workflow
        print("🔧 Initializing AI agents...")
        workflow = create_workflow(cfg)
        
        # Check if LLM is properly configured
        from .core import LLMEngine
        engine = LLMEngine(cfg)
        if not engine.is_configured():
            print("\n❌ Failed to initialize LLM engine")
            print("Please check your API key and try again")
            sys.exit(1)
        
        # Check if it's a GitHub URL
        if project_path.startswith('http://') or project_path.startswith('https://'):
            print(f"📦 Detected GitHub repository: {project_path}")
            
            # Clean up GitHub URL (remove /tree/branch parts)
            import re
            repo_url = project_path
            branch = None
            
            # Extract branch if present in URL (e.g., /tree/main)
            match = re.match(r'(https?://github\.com/[^/]+/[^/]+)(?:/tree/([^/]+))?', project_path)
            if match:
                repo_url = match.group(1)
                branch = match.group(2)
                if branch:
                    print(f"📌 Branch detected: {branch}")
            
            # Clone to temp directory
            import tempfile
            import subprocess
            
            temp_dir = tempfile.mkdtemp(prefix='setup_agent_')
            print(f"📥 Cloning repository to: {temp_dir}")
            
            try:
                clone_cmd = ['git', 'clone']
                if branch:
                    clone_cmd.extend(['-b', branch])
                clone_cmd.extend([repo_url, temp_dir])
                
                result = subprocess.run(
                    clone_cmd,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"❌ Failed to clone repository: {result.stderr}")
                    sys.exit(1)
                    
                project_path = temp_dir
                print(f"✅ Repository cloned successfully")
            except FileNotFoundError:
                print("❌ Git is not installed. Please install Git to clone repositories.")
                sys.exit(1)
        
        # Prepare initial state
        initial_state = State(
            project_path=str(Path(project_path).absolute()),
            mode=mode,
            preferences={
                'skip_verification': no_verify,
                'fast_mode': fast,
                'verbose': verbose
            }
        )
        
        # Run workflow
        print(f"🚀 Starting AI-powered setup for: {project_path}\n")
        
        # Execute workflow with thread config for memory
        thread_config = {"configurable": {"thread_id": "setup-1"}}
        
        async for event in workflow.astream(initial_state, thread_config):
            if verbose:
                # Show progress
                for node, state in event.items():
                    if node != "__end__":
                        print(f"  [{node}] Processing...")
        
        print("\n✨ Setup complete!")
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        if "API" in str(e) or "api_key" in str(e):
            print("\n💡 This looks like an API key issue.")
            print("   Please check:")
            print("   • Your API key is valid")
            print("   • You have credits/quota available")
            print("   • The API service is accessible")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()