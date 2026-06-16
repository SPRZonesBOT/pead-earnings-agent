# analysis/financial_extractor.py
import pdfplumber
import re

class FinancialExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def extract_standalone_numbers(self):
        """Extract key financial metrics from result PDF"""
        data = {}
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"

                # ---- Extract Key Numbers (Regex patterns) ----
                # Revenue
                rev_match = re.search(r'(?:Total Income|Revenue from Ops|Income from Operations)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                data['revenue'] = float(rev_match.group(1).replace(',', '')) if rev_match else 0

                # EBITDA
                ebit_match = re.search(r'(?:EBITDA|Operating Profit)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                data['ebitda'] = float(ebit_match.group(1).replace(',', '')) if ebit_match else 0

                # PAT
                pat_match = re.search(r'(?:Net Profit|PAT|Profit After Tax)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                data['pat'] = float(pat_match.group(1).replace(',', '')) if pat_match else 0

                # EPS
                eps_match = re.search(r'(?:Basic EPS|Diluted EPS)\s*\(.*?\)\s*([\d,]+\.?[\d]*)', full_text, re.I)
                data['eps'] = float(eps_match.group(1).replace(',', '')) if eps_match else 0

                # Exceptional Items
                exc_match = re.search(r'(?:Exceptional Items)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                data['exceptional_items'] = float(exc_match.group(1).replace(',', '')) if exc_match else 0

                # Finance Cost / Interest
                fin_match = re.search(r'(?:Finance Cost|Interest Expense)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                data['finance_cost'] = float(fin_match.group(1).replace(',', '')) if fin_match else 0

                # Depreciation
                dep_match = re.search(r'(?:Depreciation|Depn\.)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                data['depreciation'] = float(dep_match.group(1).replace(',', '')) if dep_match else 0

                # Calculate margins
                if data['revenue'] > 0:
                    data['pat_margin'] = (data['pat'] / data['revenue']) * 100
                    data['ebitda_margin'] = (data['ebitda'] / data['revenue']) * 100

        except Exception as e:
            print(f"PDF extraction error: {e}")
            return None

        return data
