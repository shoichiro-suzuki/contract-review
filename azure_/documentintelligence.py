# pip install python-dotenv
# pip install azure-ai-documentintelligence==1.0.2

import os
import json
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv


class DocumentIntelligenceOCR:
    def __init__(self):
        load_dotenv()
        self.endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.key = os.getenv("DOCUMENT_INTELLIGENCE_API_KEY")
        self.client = self.create_client()

    def create_client(self):
        return DocumentIntelligenceClient(self.endpoint, AzureKeyCredential(self.key))

    def analyze_document(self, file_path):
        with open(file_path, "rb") as f:
            poller = self.client.begin_analyze_document(
                "prebuilt-layout",
                body=f,
                output_content_format="markdown",
            )
            result = poller.result()
        return result


# 使用例
if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # メインウィンドウを非表示
    file_path = filedialog.askopenfilename(
        title="OCR処理するファイルを選択してください",
        filetypes=[("PDFファイル", "*.pdf")],
    )
    if not file_path:
        print("ファイルが選択されませんでした。処理を終了します。")
        exit(1)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist.")
    ocr = DocumentIntelligenceOCR()
    result = ocr.analyze_document(file_path)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_json = f"{base_name}.json"
    with open(output_json, "w", encoding="utf-8") as jf:
        json.dump(result.as_dict(), jf, ensure_ascii=False, indent=2)
    print(f"OCR結果を {output_json} に保存しました。")
