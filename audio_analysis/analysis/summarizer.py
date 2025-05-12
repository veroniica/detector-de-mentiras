"""
Module for summarizing interview transcripts and extracting main ideas.
"""

import logging
from typing import Dict, List, Any

import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
import numpy as np
from transformers import pipeline

from audio_analysis import config

logger = logging.getLogger(__name__)

# Download necessary NLTK resources
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception as e:
    logger.warning(f"Failed to download NLTK resources: {e}")


class InterviewSummarizer:
    """
    Class for summarizing interview transcripts and extracting main ideas.
    """
    
    def __init__(self, language: str = config.LANGUAGE):
        """
        Initialize the summarizer.
        
        Args:
            language: Language code for summarization
        """
        self.language = language
        
        # Initialize the summarization pipeline from transformers
        try:
            self.summarizer = pipeline(
                "summarization", 
                model="facebook/bart-large-cnn",
                truncation=True
            )
            logger.debug("Initialized transformer-based summarizer")
        except Exception as e:
            logger.error(f"Failed to initialize transformer summarizer: {e}")
            self.summarizer = None
        
        # Set up stopwords for the extractive summarization
        try:
            if language == 'es':
                self.stop_words = set(stopwords.words('spanish'))
            else:
                self.stop_words = set(stopwords.words('english'))
        except:
            logger.warning(f"Stopwords not available for {language}, using empty set")
            self.stop_words = set()
    
    def _extract_text_from_transcript(self, transcript: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from transcript for summarization.
        
        Args:
            transcript: List of transcript segments with speaker information
            
        Returns:
            Plain text of the entire transcript
        """
        return " ".join([segment["text"] for segment in transcript if "text" in segment])
    
    def _extract_main_ideas(self, text: str) -> List[str]:
        """
        Extract main ideas from the text using sentence ranking.
        
        Args:
            text: Plain text to analyze
            
        Returns:
            List of main ideas (important sentences)
        """
        # Tokenize the text into sentences
        sentences = sent_tokenize(text)
        
        if len(sentences) <= 3:
            return sentences
        
        # Create similarity matrix
        similarity_matrix = self._build_similarity_matrix(sentences)
        
        # Rank sentences using PageRank-like algorithm
        sentence_scores = self._rank_sentences(similarity_matrix)
        
        # Select top sentences as main ideas (about 30% of the original)
        num_main_ideas = max(3, int(len(sentences) * 0.3))
        ranked_sentences = [sentences[i] for i in np.argsort(sentence_scores)[-num_main_ideas:]]
        
        # Sort by original order
        main_ideas = [s for s in sentences if s in ranked_sentences]
        
        return main_ideas
    
    def _build_similarity_matrix(self, sentences: List[str]) -> np.ndarray:
        """
        Build a similarity matrix between all sentences.
        
        Args:
            sentences: List of sentences
            
        Returns:
            Similarity matrix as numpy array
        """
        # Create an empty similarity matrix
        similarity_matrix = np.zeros((len(sentences), len(sentences)))
        
        for i in range(len(sentences)):
            for j in range(len(sentences)):
                if i != j:
                    similarity_matrix[i][j] = self._sentence_similarity(
                        sentences[i], sentences[j]
                    )
        
        return similarity_matrix
    
    def _sentence_similarity(self, sent1: str, sent2: str) -> float:
        """
        Calculate similarity between two sentences using cosine similarity.
        
        Args:
            sent1: First sentence
            sent2: Second sentence
            
        Returns:
            Similarity score between 0 and 1
        """
        # Tokenize and clean sentences
        words1 = [word.lower() for word in nltk.word_tokenize(sent1) 
                 if word.isalnum() and word.lower() not in self.stop_words]
        words2 = [word.lower() for word in nltk.word_tokenize(sent2) 
                 if word.isalnum() and word.lower() not in self.stop_words]
        
        # Create word sets
        all_words = list(set(words1 + words2))
        
        # Create word vectors
        vector1 = [1 if word in words1 else 0 for word in all_words]
        vector2 = [1 if word in words2 else 0 for word in all_words]
        
        # Calculate cosine similarity
        return 1 - cosine_distance(vector1, vector2)
    
    def _rank_sentences(self, similarity_matrix: np.ndarray) -> np.ndarray:
        """
        Rank sentences using a PageRank-like algorithm.
        
        Args:
            similarity_matrix: Similarity matrix between sentences
            
        Returns:
            Array of sentence scores
        """
        # Convert similarity matrix to column-stochastic form
        column_sums = similarity_matrix.sum(axis=0)
        column_sums[column_sums == 0] = 1  # Avoid division by zero
        stochastic_matrix = similarity_matrix / column_sums
        
        # Initialize scores
        scores = np.ones(len(similarity_matrix)) / len(similarity_matrix)
        
        # Power iteration
        for _ in range(10):  # Usually converges quickly
            scores = np.dot(stochastic_matrix, scores)
        
        return scores
    
    def _generate_abstractive_summary(self, text: str) -> str:
        """
        Generate an abstractive summary using transformer models.
        
        Args:
            text: Text to summarize
            
        Returns:
            Abstractive summary
        """
        if not self.summarizer:
            return "Transformer-based summarization not available."
        
        try:
            # Split text if it's too long
            max_length = 1024
            if len(text) > max_length:
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                summaries = []
                
                for chunk in chunks:
                    summary = self.summarizer(chunk, max_length=150, min_length=30, do_sample=False)
                    summaries.append(summary[0]['summary_text'])
                
                return " ".join(summaries)
            else:
                summary = self.summarizer(text, max_length=150, min_length=30, do_sample=False)
                return summary[0]['summary_text']
        except Exception as e:
            logger.error(f"Error in abstractive summarization: {e}")
            return "Error generating abstractive summary."
    
    def summarize(self, transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize the transcript and extract main ideas.
        
        Args:
            transcript: List of transcript segments with speaker information
            
        Returns:
            Dictionary with summary and main ideas
        """
        logger.info("Generating summary and extracting main ideas")
        
        # Extract plain text from transcript
        text = self._extract_text_from_transcript(transcript)
        
        if not text:
            logger.warning("No text found in transcript for summarization")
            return {
                "summary": "",
                "main_ideas": []
            }
        
        # Extract main ideas
        main_ideas = self._extract_main_ideas(text)
        
        # Generate abstractive summary
        summary = self._generate_abstractive_summary(text)
        
        result = {
            "summary": summary,
            "main_ideas": main_ideas
        }
        
        logger.info(f"Generated summary with {len(main_ideas)} main ideas")
        return result