import os
import sys
import difflib
import importlib.util
from pathlib import Path

import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ============================
# GROQ CLIENT SETUP
# ============================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.1-8b-instant"

# ============================
# HELPER FUNCTIONS
# ============================

def read_csv_as_df(csv_path: str) -> pd.DataFrame:
    """
    Read the expected CSV and ensure correct data types for comparison.
    Empty strings in numeric columns are treated as NaN.
    """
    df = pd.read_csv(csv_path)
    # Convert numeric columns, coercing errors will turn non-numeric values into NaT/NaN
    for col in ['Debit Amt', 'Credit Amt', 'Balance']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def run_generated_code(code: str, pdf_path: str, target: str) -> pd.DataFrame:
    """
    Dynamically run the generated parser code and return a dataframe.
    The code must contain a parse(pdf_path) function.
    """
    # *** MODIFIED LINE: Use the 'target' variable for a dynamic, unique name ***
    parser_module_name = f"{target}_parser_{os.urandom(4).hex()}"
    
    temp_dir = Path("custom_parsers")
    temp_dir.mkdir(exist_ok=True)
    parser_file = temp_dir / f"{parser_module_name}.py"
    
    (temp_dir / "__init__.py").touch()

    parser_file.write_text(code, encoding="utf-8")

    try:
        spec = importlib.util.spec_from_file_location(f"custom_parsers.{parser_module_name}", parser_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"custom_parsers.{parser_module_name}"] = module
        spec.loader.exec_module(module)
        return module.parse(pdf_path)
    finally:
        # Clean up the temporary parser file
        if parser_file.exists():
            parser_file.unlink()


def ask_groq_for_parser(target: str, pdf_path: str, csv_path: str) -> str:
    """
    Ask Groq to generate parser code with a more robust prompt.
    """
    expected_df = read_csv_as_df(csv_path)
    expected_head = expected_df.head(5).to_string()

    prompt = f"""
You are an expert Python developer specializing in data extraction from PDF files.
Your task is to write a Python script to parse a bank statement PDF and return a clean pandas DataFrame.

Target Bank: {target}

The parser MUST be a Python module containing one function: parse(pdf_path: str) -> pd.DataFrame

Follow these requirements precisely:
1.  Use the `camelot-py` library to extract tables. The PDF is stream-based, so use `flavor='stream'`.
2.  The PDF may have multiple pages. You MUST combine the tables from all pages into a single DataFrame.
3.  The raw table often contains header rows or garbage data. Identify and remove any rows that are not actual transactions. A row is likely a transaction if the first column contains a valid date.
4.  After cleaning, the DataFrame must have exactly these columns in this order: ['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']
5.  Data Cleaning:
    - 'Date' column should be a string in 'DD-MM-YYYY' format.
    - 'Description' column may have newlines (`\\n`). Replace them with a space.
    - 'Debit Amt', 'Credit Amt', and 'Balance' columns MUST be numeric (float). Use `pd.to_numeric` with `errors='coerce'` to handle any non-numeric values, which will correctly convert them to `NaN`. Do NOT fill NaN with empty strings.

Here are the first few rows of the expected output DataFrame for guidance:
{expected_head}

Return ONLY the complete Python code for the parser module. Do not include any explanations, markdown, or introductory text.
    """

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a Python code generation expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content

def run_test(target: str, pdf_path: str, csv_path: str, code: str) -> tuple[bool, str]:
    """Run test by comparing generated dataframe with expected CSV."""
    if not code or not code.strip():
        return False, "LLM returned empty code."
    
    try:
        # *** MODIFIED LINE: Pass 'target' to the function ***
        df = run_generated_code(code, pdf_path, target)
    except Exception as e:
        return False, f"IMPORT/RUNTIME ERROR:\n{e}"

    expected = read_csv_as_df(csv_path)
    df.reset_index(drop=True, inplace=True)
    expected.reset_index(drop=True, inplace=True)
    
    if list(df.columns) != list(expected.columns):
        return False, f"Mismatch columns.\nExpected: {expected.columns.to_list()}\nGot: {df.columns.to_list()}"

    # Use DataFrame.equals to match the challenge specification
    if df.equals(expected):
        # NEW CODE: Save the successful output for verification
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{target}_output.csv"
        df.to_csv(output_path, index=False)
        
        success_message = (
            f"✅ Parser matched expected output!\n"
            f"   - Verification file saved to: {output_path}"
        )
        return True, success_message
    else:
        # Generate a diff for debugging when they are not equal
        diff = difflib.unified_diff(
            expected.to_string().splitlines(),
            df.to_string().splitlines(),
            lineterm=""
        )
        error_message = "Data mismatch. Debug:\n" + "\n".join(list(diff)[:40])
        return False, error_message

def make_fallback_parser_code() -> str:
    """
    A robust, deterministic Camelot-based fallback parser.
    """
    return """
import pandas as pd
import camelot

def parse(pdf_path: str) -> pd.DataFrame:
    tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")
    if not tables:
        raise ValueError("No tables found in PDF")
    df = pd.concat([table.df for table in tables], ignore_index=True)
    header_index = -1
    for i, row in df.iterrows():
        if 'Date' in str(row[0]) and 'Description' in str(row[1]):
            header_index = i
            break
    if header_index != -1:
        df.columns = df.iloc[header_index]
        df = df.iloc[header_index + 1:].reset_index(drop=True)
    if df.shape[1] == 5:
        df.columns = ['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']
    else:
        df = df[df[0].str.match(r'\\d{2}-\\d{2}-\\d{4}', na=False)]
        df = df.iloc[:, :5]
        df.columns = ['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']
    df['Description'] = df['Description'].str.replace('\\n', ' ', regex=False).str.strip()
    for col in ['Debit Amt', 'Credit Amt', 'Balance']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=['Date'], inplace=True)
    df = df[df['Date'].str.match(r'\\d{2}-\\d{2}-\\d{4}', na=False)].reset_index(drop=True)
    return df
"""

def save_parser_code(target: str, code: str):
    """Saves the provided code to the parser file."""
    if not code or not code.strip():
        print("❌ ERROR: Attempted to save empty code. Aborting.")
        return

    # Ensure the custom_parsers directory exists
    output_dir = Path("custom_parsers")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "__init__.py").touch()

    # Define the output file path
    parser_path = output_dir / f"{target}_parser.py"

    # --- DEBUGGING STEP ---
    print(f"\nWriting the following code to {parser_path}:")
    print("--- CODE START ---")
    print('\n'.join(code.split('\n')[:5])) # Printing the first 5 lines of the code
    print("... (and more)")
    print("--- CODE END ---\n")

    parser_path.write_text(code, encoding="utf-8")
    print(f"✅ Successfully saved parser to {parser_path}")

# ============================
# MAIN LOOP
# ============================

def main():
    if len(sys.argv) < 3 or sys.argv[1] != "--target":
        print("Usage: python agent.py --target <bank_name>")
        sys.exit(1)

    target = sys.argv[2]
    print(f"\n Running agent for target: {target}\n")

    pdf_path = Path(f"data/{target}/{target}_sample.pdf")
    csv_path = Path(f"data/{target}/{target}_sample.csv")
    
    if not pdf_path.exists() or not csv_path.exists():
        print(f"Error: Missing files. Ensure '{pdf_path}' and '{csv_path}' exist.")
        sys.exit(1)

    max_attempts = 3
    success = False

    for attempt in range(1, max_attempts + 1):
        print(f"--- ATTEMPT {attempt}/{max_attempts} ---")
        try:
            code = ask_groq_for_parser(target, str(pdf_path), str(csv_path))
            if code.strip().startswith("```python"):
                code = code.strip()[9:].strip("`").strip()

            ok, message = run_test(target, str(pdf_path), str(csv_path), code)
            
            if ok:
                print(message)
                save_parser_code(target, code)
                success = True
                break
            else:
                print(f"Attempt {attempt} failed: {message}")
        except Exception as e:
            print(f"An unexpected error occurred in attempt {attempt}: {e}")

    if not success:
        print("\n LLM attempts exhausted — trying deterministic fallback parser.")
        fb_code = make_fallback_parser_code()
        ok, message = run_test(target, str(pdf_path), str(csv_path), fb_code)
        if ok:
            print(message) # The success message now includes the output path
            save_parser_code(target, fb_code)
        else:
            print(f"❌ Fallback parser did NOT match expected CSV. Debug:\n{message}")

if __name__ == "__main__":
    main()