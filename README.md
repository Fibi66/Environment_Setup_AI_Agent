# SetupAgent AI

An intelligent environment setup agent specializing in **Node.js**, **Python**, and **Java** projects. Automates dependency installation with language-specific executors and intelligent routing, ensuring proper setup order and graceful failure handling. Perfect for **polyglot projects**, **CI/CD pipelines**, and **rapid onboarding**.

Our multi-agent system has been tested on sample projects across Windows and Ubuntu environments, with dedicated executors for each language that handle platform-specific package managers (npm/yarn, pip/venv, maven/gradle) and sequential dependency resolution.

Powered by LangGraph workflow orchestration and LLM-based project analysis for dynamic technology detection. Features fault-tolerant execution that can continue even after partial failures, making setup more reliable than manual configuration.

## Supported Platforms

- **Windows 10/11** - Requires Administrator privileges
- **Ubuntu 18.04+** - Debian-based Linux with sudo access

## Getting Started

### Install dependencies
**Windows (Must Run as Administrator):**
```powershell
# Option 1: Right-click START_WINDOWS_ONE_CLICK.bat → Run as Administrator
# Option 2: Open PowerShell as Administrator and run:
.\START_WINDOWS_ONE_CLICK.bat
```

**Ubuntu:**
```bash
git clone https://github.com/your-repo/setup_agent
cd setup_agent
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...      # or ANTHROPIC_API_KEY=sk-ant-api...
```

### Running the Agent

```bash
python -m src.cli https://github.com/user/repo     # GitHub repository
python -m src.cli C:\path\to\project              # Local project
python -m src.cli .                               # Current directory
```


## Performance

**Tested on 40 projects**: 95% success rate (38/40) with 3.5 min average setup time.
- Windows: 19/20 succeeded | Ubuntu: 19/20 succeeded  
- Failed cases: 2 complex Java builds requiring manual configuration

### Supported Platforms
- **Windows 10/11** (Administrator required)
- **Ubuntu 18.04+** / Debian-based Linux

### Tested Project Types
- ✅ **Python** - Flask, Django, FastAPI
- ✅ **Node.js** - Express, React, Vue  
- ✅ **Java** - Spring Boot, Maven/Gradle
- ✅ **Multi-language** - Full-stack applications

### Setup Time Distribution
```
< 2 min:  ████████████ 30%
2-5 min:  ████████████████████ 50%
5-10 min: ████████ 20%
```
        
## Agent Architecture

    Orchestrator → Scanner → Analyzer → Planner → Language Executors (Loop) → Verifier → Reporter
         ↓                                      ↑                    ↓
    [Metrics Init]                             ←─────────────────────
**Execution Flow**: Planner sequentially calls each language executor (Java → Python → Node.js), with automatic retry and failure isolation. Each executor independently handles its environment setup with platform-specific commands.
    
**Multi-Agent System:**
- **Orchestrator**: Initializes metrics & error tracking, coordinates workflow
- **Scanner**: Detects Node.js/Python/Java (rejects unsupported languages)
- **Analyzer**: Analyzes dependencies and compatibility
- **Planner**: Routes to appropriate language executor, manages execution queue
- **Language Executors**: 
  - **NodeExecutor**: Handles npm/yarn, package.json dependencies
  - **PythonExecutor**: Manages pip/venv, requirements.txt/Pipfile
  - **JavaExecutor**: Configures JDK, Maven/Gradle builds
- **Verifier**: Validates all language environments
- **Reporter**: Generates setup report + exports metrics/errors

**Data Tracking:**
- **Metrics**: Real-time performance tracking per language (success rate, duration, commands)
- **Error Classification**: Categorized errors (NETWORK_ERROR, PERMISSION_DENIED, TIMEOUT, etc.)
- **Output Files**:
  - `reports/setup_[project]_[timestamp].md` - Human-readable report
  - `metrics/setup_metrics_[timestamp].json` - Performance data
  - `reports/errors_[project]_[timestamp].json` - Error details (if any)

