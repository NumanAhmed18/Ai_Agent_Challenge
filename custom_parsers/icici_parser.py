import camelot
import pandas as pd

def parse(pdf_path: str) -> pd.DataFrame:
    tables = camelot.read_pdf(pdf_path, flavor='stream', pages='all')
    df = pd.concat([table.df for table in tables], ignore_index=True)

    # Remove rows that are not actual transactions
    df = df[df.iloc[:, 0].str.contains('\d{2}-\d{2}-\d{4}').fillna(False)]

    # Clean the columns
    df['Date'] = df.iloc[:, 0].str.extract('(\d{2}-\d{2}-\d{4})')
    df['Description'] = df.iloc[:, 1].str.replace('\n', ' ')
    df['Debit Amt'] = pd.to_numeric(df.iloc[:, 2], errors='coerce')
    df['Credit Amt'] = pd.to_numeric(df.iloc[:, 3], errors='coerce')
    df['Balance'] = pd.to_numeric(df.iloc[:, 4], errors='coerce')

    # Reorder the columns
    df = df[['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']]

    return df