import sys
import fitz
import re


def extract_gift_card_code(pdf_path):
    """
    Extract Wolt gift card code from PDF.
    The code is typically 8 characters long, alphanumeric and uppercase.
    """
    print(f"Opening PDF: {pdf_path}")

    with fitz.open(pdf_path) as doc:
        print(f"PDF has {len(doc)} pages")

        for page_num, page in enumerate(doc):
            print(f"Processing page {page_num+1}")
            text = page.get_text()

            # Print the entire text for debugging
            print(f"Page text: {text}")

            # Look for a pattern that matches Wolt gift card codes
            # Common patterns:
            # 1. 8 character alphanumeric code (e.g., "ABC12345")
            # 2. Hebrew text with the word "קוד" (code) followed by the gift card code
            # 3. "code:" or "code" followed by the gift card code

            # First attempt: Find 8 character alphanumeric code
            code_pattern = re.compile(r"\b[A-Z0-9]{8}\b")
            matches = code_pattern.findall(text)
            if matches:
                print(f"Found potential codes via pattern 1: {matches}")
                return matches[0]

            # Second attempt: Look for lines with 'קוד' (Hebrew for "code")
            for line in text.split("\n"):
                print(f"Analyzing line: {line}")
                if "קוד" in line:
                    print(f"Found 'code' in Hebrew in line: {line}")
                    # Extract alphanumeric sequences that could be codes
                    code_candidates = re.findall(r"\b[A-Z0-9]{7,9}\b", line)
                    if code_candidates:
                        print(f"Found potential codes in this line: {code_candidates}")
                        return code_candidates[0]

            # Third attempt: Look for "code:" or "code" followed by text
            code_prefix_pattern = re.compile(
                r"(?:code|code:)\s*([A-Z0-9]{7,9})", re.IGNORECASE
            )
            for line in text.split("\n"):
                match = code_prefix_pattern.search(line)
                if match:
                    print(f"Found code via 'code:' pattern: {match.group(1)}")
                    return match.group(1)

    print("No gift card code found in this PDF")
    return None


def extract_gift_card_value(pdf_text):
    """
    Extract the gift card value from PDF text.
    Returns the value as an integer (in the local currency units).
    The pattern to look for is typically "60.00 ₪" where 60 can be any number.
    """
    print(f"Extracting gift card value from PDF text")

    # Look for amount with decimal places followed by shekel symbol (e.g., "60.00 ₪")
    shekel_decimal_pattern = re.compile(r"(\d+)\.00\s*₪")
    match = shekel_decimal_pattern.search(pdf_text)
    if match:
        value = int(match.group(1))
        print(f"Found gift card value using primary pattern: {value}")
        return value

    # Backup pattern: Look for amount with currency symbol (₪)
    shekel_pattern = re.compile(r"(?:₪\s*(\d+))|(?:(\d+)\s*₪)")
    match = shekel_pattern.search(pdf_text)
    if match:
        # Get the first non-None group
        value_str = match.group(1) if match.group(1) else match.group(2)
        value = int(value_str)
        print(f"Found gift card value using shekel symbol pattern: {value}")
        return value

    # Look for "ILS" pattern
    ils_pattern = re.compile(r"(?:ILS\s*(\d+)(?:\.\d+)?)|(?:(\d+)(?:\.\d+)?\s*ILS)")
    match = ils_pattern.search(pdf_text)
    if match:
        value_str = match.group(1) if match.group(1) else match.group(2)
        value = int(float(value_str))
        print(f"Found gift card value using ILS pattern: {value}")
        return value

    # Default value if we can't extract it
    print("No gift card value found in PDF, using default value: 0")
    return 0  # Assuming 0 ILS as default value if not found


def extract_pdf_text(pdf_path):
    """
    Extract all text content from a PDF file.
    Returns the text as a single string.
    """
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")

    return text


def extract_gift_card_info(pdf_path):
    """
    Extract both the gift card code and full text from a PDF.
    Returns a tuple of (code, text).
    """
    code = extract_gift_card_code(pdf_path)
    text = extract_pdf_text(pdf_path)
    return code, text


def extract_gift_card_details(pdf_path):
    """
    Extract gift card code and value from a PDF.
    Returns a tuple of (code, value).
    """
    code = extract_gift_card_code(pdf_path)
    if not code:
        return None, 0  # Default value if no code found

    text = extract_pdf_text(pdf_path)
    value = extract_gift_card_value(text)

    return code, value


if __name__ == "__main__":
    path = sys.argv[1]
    code = extract_gift_card_code(path)
    print("Extracted Wolt gift card code:", code)
