import os
import pdfplumber

input_path = "app/components/generate_tables/data/input"

def classify_pdf_file(input_path):
    classifications = {}
    try:
        # Process the first PDF found

        for file in os.listdir(input_path):
            if file.lower().endswith(".pdf"):
                file_path = os.path.join(input_path, file)
                print(f"Opening: {file_path}")
                text = ""

                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text.lower()

                # Rule-based classification
                if "brand store dacia" in text:
                    if "gpb" in text:
                        print("dacia-v2")
                        return "dacia-v2"
                    else:
                        print("dacia-v1")
                        return "dacia-v1"
                else:
                    if "gpb" in text:
                        print("renault-v2")
                        return "renault-v2"
                    else:
                        print("renault-v1")
                        return "renault-v1"
            print(f"data extracted from {file_path}")

    except Exception as e:
        print("Error:", e)
        return None



        
        
    