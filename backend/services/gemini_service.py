import time
from typing import Tuple

from google import genai
from google.genai import types

from core.config import Settings


class GeminiService:
    """
    Handles all Gemini File Search operations:
    - Creating/managing file search stores
    - Uploading and importing files
    - Generating AI summaries and keywords
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self.model = settings.gemini_model
        self._store_name = None

    def get_or_create_store(self) -> str:
        """
        Get or create a File Search store for the application.
        Uses a singleton pattern - creates once and reuses.

        Returns:
            str: Full resource name of the store (e.g., 'fileSearchStores/abc123')
        """
        if self._store_name:
            return self._store_name

        # Try to list existing stores
        stores = list(self.client.file_search_stores.list())
        
        # Look for our app's store
        for store in stores:
            if store.display_name == "servless-rag-store":
                self._store_name = store.name
                return self._store_name

        # Create new store if not found
        store = self.client.file_search_stores.create(
            config={"display_name": "servless-rag-store"}
        )
        self._store_name = store.name
        return self._store_name

    async def upload_and_index_file(
        self, file_path: str, display_name: str
    ) -> Tuple[str, str]:
        """
        Upload a file to Gemini File Search and wait for indexing to complete.

        Args:
            file_path: Local path to the file
            display_name: Display name for the file in Gemini

        Returns:
            Tuple[str, str]: (store_name, document_name)
        """
        store_name = self.get_or_create_store()

        # Upload and import the file
        operation = self.client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_name,
            config={"display_name": display_name},
        )

        # Wait for the import operation to complete
        while not operation.done:
            time.sleep(2)
            operation = self.client.operations.get(operation)

        # Extract document name from operation metadata
        # The operation response contains the imported document info
        if hasattr(operation, "metadata") and operation.metadata:
            # Document name is typically in the format: fileSearchStores/{store}/documents/{doc}
            document_name = getattr(operation.metadata, "document_name", None)
            if document_name:
                return store_name, document_name

        return store_name, None

    async def generate_summary_and_keywords(
        self, file_content: str, filename: str
    ) -> Tuple[str, list[str]]:
        """
        Generate AI summary and keywords for a file.

        Args:
            file_content: The text content of the file
            filename: Name of the file

        Returns:
            Tuple[str, list[str]]: (summary, keywords)
        """
        prompt = f"""Analyze this document and provide:
1. A concise 3-line summary (max 300 characters)
2. 2-6 relevant keywords

Document name: {filename}

Document content:
{file_content[:5000]}  

Format your response as:
SUMMARY: [your summary here]
KEYWORDS: [keyword1, keyword2, keyword3, ...]
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )

            if not response.text:
                return "No summary available", []

            # Parse the response
            text = response.text
            summary = ""
            keywords = []

            for line in text.split("\n"):
                if line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                elif line.startswith("KEYWORDS:"):
                    kw_text = line.replace("KEYWORDS:", "").strip()
                    keywords = [
                        k.strip().strip("[]")
                        for k in kw_text.split(",")
                        if k.strip()
                    ]

            # Fallback if parsing fails
            if not summary:
                summary = text[:300] if text else "No summary available"
            if not keywords:
                keywords = []

            return summary[:300], keywords[:6]

        except Exception as e:
            print(f"Failed to generate summary: {e}")
            return "Summary generation failed", []

    async def chat_with_store(self, store_name: str, message: str) -> str:
        """
        Send a chat message to Gemini with File Search context.

        Args:
            store_name: Full resource name of the file search store
            message: User's question/message

        Returns:
            str: AI response
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=message,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ]
            ),
        )

        return response.text if response.text else "No response generated"
