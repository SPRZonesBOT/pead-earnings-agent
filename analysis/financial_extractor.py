# analysis/financial_extractor.py
import pdfplumber
import re
import pandas as pd

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

                # 1. Revenue / Total Income
                revenue_match = re.search(r'(?:Total Income|Revenue from Ops|Income from Operations)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                if revenue_match:
                    data['revenue'] = float(revenue_match.group(1).replace(',', ''))

                # 2. EBITDA / Operating Profit
                ebitda_match = re.search(r'(?:EBITDA|Operating Profit)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                if ebitda_match:
                    data['ebitda'] = float(ebitda_match.group(1).replace(',', ''))

                # 3. Net Profit (PAT)
                pat_match = re.search(r'(?:Net Profit|PAT|Profit After Tax)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                if pat_match:
                    data['pat'] = float(pat_match.group(1).replace(',', ''))

                # 4. Exceptional Items (if any)
                exc_match = re.search(r'(?:Exceptional Items)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                data['exceptional_items'] = float(exc_match.group(1).replace(',', '')) if exc_match else 0

                # 5. Basic EPS
                eps_match = re.search(r'(?:Basic EPS|Diluted EPS)\s*\(.*?\)\s*([\d,]+\.?[\d]*)', full_text, re.I)
                if eps_match:
                    data['eps'] = float(eps_match.group(1).replace(',', ''))

                # 6. Finance Cost / Interest
                fin_match = re.search(r'(?:Finance Cost|Interest Expense)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                if fin_match:
                    data['finance_cost'] = float(fin_match.group(1).replace(',', ''))

                # 7. Depreciation
                dep_match = re.search(r'(?:Depreciation|Depn\.)\s*[\d,]+\.?[\d]*\s*([\d,]+\.?[\d]*)', full_text, re.I)
                if dep_match:
                    data['depreciation'] = float(dep_match.group(1).replace(',', ''))

        except Exception as e:
            print(f"PDF extraction failed: {e}")
            return None

        # Calculate derived metrics
        if data.get('pat') and data.get('revenue'):
            data['pat_margin'] = (data['pat'] / data['revenue']) * 100
        if data.get('ebitda') and data.get('revenue'):
            data['ebitda_margin'] = (data['ebitda'] / data['revenue']) * 100
            
        return data
