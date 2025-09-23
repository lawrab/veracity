"""
NLP processing service for text analysis.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import spacy
import torch
from sentence_transformers import SentenceTransformer
from transformers import (
    pipeline,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class NLPProcessor:
    """Handles all NLP processing tasks."""

    def __init__(self):
        self.sentiment_pipeline = None
        self.embedding_model = None
        self.nlp_model = None
        self.classification_pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def initialize(self):
        """Initialize all NLP models."""
        try:
            logger.info("Initializing NLP models...")

            # Load sentiment analysis pipeline
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=0 if self.device == "cuda" else -1,
            )

            # Load embedding model for similarity
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

            # Load spaCy for NER and linguistic analysis
            try:
                self.nlp_model = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found, downloading...")
                spacy.cli.download("en_core_web_sm")
                self.nlp_model = spacy.load("en_core_web_sm")

            # Load classification pipeline for content categorization
            self.classification_pipeline = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=0 if self.device == "cuda" else -1,
            )

            logger.info(f"NLP models initialized on {self.device}")

        except Exception as e:
            logger.exception(f"Failed to initialize NLP models: {e}")
            raise

    async def process_text(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Process text through complete NLP pipeline."""
        try:
            # Clean and prepare text
            cleaned_text = self._clean_text(text)

            if len(cleaned_text.strip()) < 10:  # Skip very short texts
                return None

            # Run all processing tasks concurrently
            sentiment_task = asyncio.create_task(self._analyze_sentiment(cleaned_text))
            entities_task = asyncio.create_task(self._extract_entities(cleaned_text))
            keywords_task = asyncio.create_task(self._extract_keywords(cleaned_text))
            embedding_task = asyncio.create_task(self._generate_embedding(cleaned_text))
            category_task = asyncio.create_task(self._classify_content(cleaned_text))
            language_task = asyncio.create_task(self._detect_language(cleaned_text))

            # Wait for all tasks to complete
            (
                sentiment,
                entities,
                keywords,
                embedding,
                category,
                language,
            ) = await asyncio.gather(
                sentiment_task,
                entities_task,
                keywords_task,
                embedding_task,
                category_task,
                language_task,
                return_exceptions=True,
            )

            # Compile results
            return {
                "sentiment": (
                    sentiment if not isinstance(sentiment, Exception) else None
                ),
                "entities": entities if not isinstance(entities, Exception) else [],
                "keywords": keywords if not isinstance(keywords, Exception) else [],
                "embedding": (
                    embedding if not isinstance(embedding, Exception) else None
                ),
                "category": category if not isinstance(category, Exception) else None,
                "language": language if not isinstance(language, Exception) else "en",
                "processed_at": datetime.utcnow().isoformat(),
                "model_versions": {
                    "sentiment": "cardiffnlp/twitter-roberta-base-sentiment-latest",
                    "embedding": settings.EMBEDDING_MODEL,
                    "ner": "en_core_web_sm",
                    "classification": "facebook/bart-large-mnli",
                },
            }

        except Exception as e:
            logger.exception(f"Error processing text: {e}")
            return None

    async def _analyze_sentiment(self, text: str) -> float | None:
        """Analyze sentiment of text."""
        try:
            result = self.sentiment_pipeline(text[:512])  # Truncate for model limits

            # Convert to normalized score (-1 to 1)
            label = result[0]["label"]
            score = result[0]["score"]

            if label == "LABEL_2":  # Positive
                return score
            if label == "LABEL_0":  # Negative
                return -score
            # Neutral (LABEL_1)
            return 0.0

        except Exception as e:
            logger.exception(f"Error in sentiment analysis: {e}")
            return None

    async def _extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Extract named entities from text."""
        try:
            doc = self.nlp_model(text[:1000])  # Limit text length

            entities = []
            for ent in doc.ents:
                entities.append(
                    {
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "confidence": float(ent._.get("confidence", 0.5)),
                    }
                )

            return entities

        except Exception as e:
            logger.exception(f"Error in entity extraction: {e}")
            return []

    async def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        try:
            doc = self.nlp_model(text)

            # Extract meaningful tokens (nouns, proper nouns, adjectives)
            keywords = []
            for token in doc:
                if (
                    token.pos_ in ["NOUN", "PROPN", "ADJ"]
                    and not token.is_stop
                    and not token.is_punct
                    and len(token.text) > 2
                    and token.is_alpha
                ):
                    keywords.append(token.lemma_.lower())

            # Remove duplicates and return top keywords
            return list(set(keywords))[:20]

        except Exception as e:
            logger.exception(f"Error in keyword extraction: {e}")
            return []

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector for text."""
        try:
            embedding = self.embedding_model.encode(text[:512])
            return embedding.tolist()

        except Exception as e:
            logger.exception(f"Error generating embedding: {e}")
            return None

    async def _classify_content(self, text: str) -> str | None:
        """Classify content into categories."""
        try:
            categories = [
                "politics",
                "technology",
                "sports",
                "entertainment",
                "business",
                "health",
                "science",
                "world news",
                "local news",
                "opinion",
                "breaking news",
            ]

            result = self.classification_pipeline(text[:512], categories)
            return result["labels"][0] if result["scores"][0] > 0.3 else "general"

        except Exception as e:
            logger.exception(f"Error in content classification: {e}")
            return None

    async def _detect_language(self, text: str) -> str:
        """Detect language of text."""
        try:
            doc = self.nlp_model(text[:100])
            return doc.lang_ if hasattr(doc, "lang_") else "en"

        except Exception as e:
            logger.exception(f"Error in language detection: {e}")
            return "en"

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        import re

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove URLs
        text = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "",
            text,
        )

        # Remove excessive punctuation
        text = re.sub(r"[!]{2,}", "!", text)
        text = re.sub(r"[?]{2,}", "?", text)
        text = re.sub(r"[.]{3,}", "...", text)

        return text.strip()

    async def batch_process(
        self, texts: list[str], batch_size: int = 32
    ) -> list[dict[str, Any]]:
        """Process multiple texts in batches."""
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self.process_text(text) for text in batch], return_exceptions=True
            )

            results.extend(
                [
                    result if not isinstance(result, Exception) else None
                    for result in batch_results
                ]
            )

        return results

    async def similarity_search(
        self, query_text: str, candidate_texts: list[str], top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Find most similar texts to query."""
        try:
            # Generate embeddings
            query_embedding = self.embedding_model.encode(query_text)
            candidate_embeddings = self.embedding_model.encode(candidate_texts)

            # Calculate similarities
            from sklearn.metrics.pairwise import cosine_similarity

            similarities = cosine_similarity([query_embedding], candidate_embeddings)[0]

            # Get top-k results
            top_indices = similarities.argsort()[-top_k:][::-1]

            results = []
            for idx in top_indices:
                results.append(
                    {
                        "text": candidate_texts[idx],
                        "similarity": float(similarities[idx]),
                        "index": int(idx),
                    }
                )

            return results

        except Exception as e:
            logger.exception(f"Error in similarity search: {e}")
            return []
