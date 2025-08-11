# AI-Test-Case-Generator

Agent AI is an intelligent test case generator that automatically creates `pytest` test suites for Python code using AI/LLM technology.  
It helps developers quickly achieve comprehensive test coverage without manually writing tests.

  Features
- Multi-LLM Support: Works with Google Gemini, OpenAI, or a local fallback generator.
- Smart Code Analysis: Uses AST parsing and Radon to understand code structure and complexity.
- Automatic Test Generation: Generates unit, integration, edge, and error path tests.
- Real-time Execution: Runs tests instantly with coverage analysis.
- Multiple Interfaces: Command Line, Web UI, and REST API.


To run the model:

1. Create Virtual Environment

python -m venv .venv

2. Activate Environment

.\.venv\Scripts\Activate.ps1


3. Upgrade pip & Install Dependencies

pip install --upgrade pip
pip install -r requirements.txt

4. API Key Setup
You need a Google Gemini API Key (or OpenAI API key) for LLM-based test generation.


$Env:GEMINI_API_KEY = "YOUR_API_KEY"
setx GEMINI_API_KEY "YOUR_API_KEY"

5. To run Model 

python -m app.cli examples\math_utils.py --write-out tests_generated_math_utils.py

python -m uvicorn app.api:app --reload --port 8000

Open your browser at: http://127.0.0.1:8000
