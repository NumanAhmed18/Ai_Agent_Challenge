# AI Agent for Bank Statement Parsing

This project contains a Python-based AI agent that autonomously generates, tests, and debugs custom parsers for PDF bank statements. The agent uses the Groq API with Llama 3.1 to write code on the fly and is designed to be a general-purpose tool for handling statements from various banks.

This project was built to fulfill the requirements of the "Agent-as-Coder" Challenge.

---
## 🏛️ Agent Architecture & Workflow

The agent operates on a robust, multi-layered strategy that combines the power of an LLM with a reliable fallback mechanism. The core of the agent is a self-correction loop that allows it to handle errors and iteratively improve the code it generates.

The following flowchart illustrates the agent's decision-making process:

![agent_flowchart](https://github.com/user-attachments/assets/43172169-df0b-4c51-a1a1-22d6bee1d6fb)


1.  **Initialization**: The agent starts by reading the target bank and associated data files.
2.  **Self-Correction Loop**: It enters a loop with a maximum of 3 attempts.
3.  **Code Generation**: It prompts the Groq LLM to generate a custom Python parser for the PDF.
4.  **Testing**: The new code is executed, and its output DataFrame is compared against a ground-truth CSV file using `DataFrame.equals`.
5.  **Decision & Loop Control**:
    * If the test passes, the agent proceeds to the success state.
    * If the test fails, it loops back to generate new code, learning from the previous failure.
6.  **Fallback Mechanism**: If the LLM fails all attempts, the agent uses an internal, deterministic parser as a safety net.
7.  **Success & Output**: Upon success, the agent saves two files:
    * The final, working parser code in `custom_parsers/`.
    * A verification CSV file in `output/`.

---
## 🚀 Getting Started

Follow these instructions to run the AI agent on your local machine.

### Prerequisites

* Python 3.10+
* An API key from [Groq](https://console.groq.com/keys)

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd ai-agent-challenge
```

### 2. Set Up a Virtual Environment

It's recommended to use a virtual environment to manage dependencies.

```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install the required Python libraries from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Set Up Your API Key

Create a file named `.env` in the root of the project directory. Add your Groq API key to this file:

```
GROQ_API_KEY="your-groq-api-key-here"
```

### 5. Run the Agent

Execute the agent from your terminal, specifying the target bank. The sample data for `icici` is included.

```bash
python agent.py --target icici
```

The agent will begin its process. Upon completion, you will find the generated parser in the `custom_parsers/` directory and the final CSV in the `output/` directory.

### 6. Run the Automated Tests (Optional)

To verify the generated parser against the formal test suite, run `pytest`:

```bash
pytest
```

A "green" or "passed" message confirms that the agent's output is correct.

---
## ✨ Features

* **Autonomous Code Generation**: Uses an LLM to write Python code from scratch.
* **Self-Debugging Loop**: Automatically retries and corrects itself upon encountering errors.
* **Extensible**: Easily adaptable to new banks by providing new sample files and changing the `--target` flag.
* **Robust Fallback**: Includes a deterministic parser to ensure success even when the LLM fails.
* **Verifiable Output**: Generates both the parser code and a final output CSV for easy verification.
