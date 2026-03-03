"""
Custom Embedding Functions for Vector Stores
Avoids Windows DLL issues with onnxruntime by using OpenAI directly
Compatible with both ChromaDB and pgvector
"""

import os
import logging
from typing import List
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbeddings:
    """
    Custom OpenAI embedding function that works reliably on Windows
    Compatible with ChromaDB's embedding function interface
    """
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required for embeddings")
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"Initialized OpenAI embeddings with model: {model}")
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts
        
        Args:
            input: List of text strings to embed
            
        Returns:
            List of embedding vectors (lists of floats)
        """
        try:
            # OpenAI API call
            response = self.client.embeddings.create(
                model=self.model,
                input=input
            )
            
            # Extract embeddings in order
            embeddings = [item.embedding for item in response.data]
            
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

