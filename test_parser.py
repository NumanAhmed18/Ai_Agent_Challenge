import pandas as pd
from pathlib import Path

# NOTE: This assumes your agent has already run and created this file.
from custom_parsers.icici_parser import parse

def test_icici_parser_output():
    """
    Tests that the agent-generated parser for ICICI produces a DataFrame
    that exactly matches the sample CSV.
    """
    # Define the paths to the data files
    pdf_path = Path("data/icici/icici_sample.pdf")
    csv_path = Path("data/icici/icici_sample.csv")

    # 1. Get the actual DataFrame from the generated parser
    actual_df = parse(str(pdf_path))

    # 2. Get the expected DataFrame from the ground-truth CSV file
    expected_df = pd.read_csv(csv_path)
    # Ensure numeric columns are handled correctly
    for col in ['Debit Amt', 'Credit Amt', 'Balance']:
        expected_df[col] = pd.to_numeric(expected_df[col], errors='coerce')

    # --- FIX: Reset the index on both DataFrames before comparing ---
    actual_df.reset_index(drop=True, inplace=True)
    expected_df.reset_index(drop=True, inplace=True)

    # 3. Assert that the two DataFrames are equal.
    assert actual_df.equals(expected_df), "Parsed DataFrame does not match the expected CSV."