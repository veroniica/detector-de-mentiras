"""
Module for detecting inconsistencies between different interviews.
"""

import logging
from typing import Dict, List, Any, Tuple, Set

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from audio_analysis import config

logger = logging.getLogger(__name__)

# Download necessary NLTK resources
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception as e:
    logger.warning(f"Failed to download NLTK resources: {e}")


class InconsistencyDetector:
    """
    Class for detecting inconsistencies between different interviews.
    """
    
    def __init__(self, language: str = config.LANGUAGE, 
                similarity_threshold: float = config.INCONSISTENCY_SIMILARITY_THRESHOLD):
        """
        Initialize the inconsistency detector.
        
        Args:
            language: Language code for text processing
            similarity_threshold: Threshold for determining similar statements
        """
        self.language = language
        self.similarity_threshold = similarity_threshold
        
        # Set up stopwords
        try:
            if language == 'es':
                self.stop_words = set(stopwords.words('spanish'))
            else:
                self.stop_words = set(stopwords.words('english'))
        except:
            logger.warning(f"Stopwords not available for {language}, using empty set")
            self.stop_words = set()
        
        # Initialize TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            stop_words=list(self.stop_words),
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.85
        )
    
    def _extract_statements_by_speaker(self, transcript: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Extract statements by each speaker from the transcript.
        
        Args:
            transcript: List of transcript segments with speaker information
            
        Returns:
            Dictionary mapping speakers to their statements
        """
        statements_by_speaker = {}
        
        for segment in transcript:
            if "text" not in segment or not segment["text"]:
                continue
            
            speaker = segment.get("speaker", "Unknown")
            if speaker not in statements_by_speaker:
                statements_by_speaker[speaker] = []
            
            # Split text into sentences
            sentences = sent_tokenize(segment["text"])
            for sentence in sentences:
                if len(sentence.split()) >= 3:  # Only consider sentences with at least 3 words
                    statements_by_speaker[speaker].append({
                        "text": sentence,
                        "start_time": segment["start_time"],
                        "end_time": segment["end_time"],
                        "start_timestamp": segment["start_timestamp"],
                        "end_timestamp": segment["end_timestamp"]
                    })
        
        return statements_by_speaker
    
    def _find_similar_statements(self, statements_list: List[Dict[str, Any]]) -> List[Tuple[int, int, float]]:
        """
        Find similar statements in a list using TF-IDF and cosine similarity.
        
        Args:
            statements_list: List of statement dictionaries
            
        Returns:
            List of tuples (index1, index2, similarity_score)
        """
        if len(statements_list) < 2:
            return []
        
        # Extract text from statements
        texts = [statement["text"] for statement in statements_list]
        
        # Create TF-IDF matrix
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
        except:
            # If vectorization fails (e.g., all words filtered out), use a simpler approach
            logger.warning("TF-IDF vectorization failed, using simpler approach")
            return self._find_similar_statements_simple(statements_list)
        
        # Calculate cosine similarity
        cosine_sim = cosine_similarity(tfidf_matrix)
        
        # Find pairs of similar statements
        similar_pairs = []
        for i in range(len(cosine_sim)):
            for j in range(i + 1, len(cosine_sim)):
                similarity = cosine_sim[i][j]
                if similarity >= self.similarity_threshold:
                    similar_pairs.append((i, j, similarity))
        
        return similar_pairs
    
    def _find_similar_statements_simple(self, statements_list: List[Dict[str, Any]]) -> List[Tuple[int, int, float]]:
        """
        Simpler approach to find similar statements using word overlap.
        
        Args:
            statements_list: List of statement dictionaries
            
        Returns:
            List of tuples (index1, index2, similarity_score)
        """
        similar_pairs = []
        
        for i in range(len(statements_list)):
            words_i = set(word_tokenize(statements_list[i]["text"].lower()))
            words_i = words_i - self.stop_words
            
            for j in range(i + 1, len(statements_list)):
                words_j = set(word_tokenize(statements_list[j]["text"].lower()))
                words_j = words_j - self.stop_words
                
                if not words_i or not words_j:
                    continue
                
                # Calculate Jaccard similarity
                similarity = len(words_i.intersection(words_j)) / len(words_i.union(words_j))
                
                if similarity >= self.similarity_threshold:
                    similar_pairs.append((i, j, similarity))
        
        return similar_pairs
    
    def _detect_contradictions(self, similar_statements: List[Tuple[Dict[str, Any], Dict[str, Any], float]]) -> List[Dict[str, Any]]:
        """
        Detect potential contradictions among similar statements.
        
        Args:
            similar_statements: List of tuples (statement1, statement2, similarity)
            
        Returns:
            List of potential contradictions
        """
        contradictions = []
        
        # Keywords that might indicate negation or contradiction
        negation_words = {
            'es': ['no', 'nunca', 'jamás', 'ni', 'tampoco', 'nada', 'nadie', 'ninguno', 'ninguna'],
            'en': ['no', 'not', 'never', 'none', 'nobody', 'nothing', 'neither', 'nor']
        }
        
        neg_words = negation_words.get(self.language, negation_words['en'])
        
        for stmt1, stmt2, similarity in similar_statements:
            # Check if one statement contains negation and the other doesn't
            stmt1_has_negation = any(neg in word_tokenize(stmt1["text"].lower()) for neg in neg_words)
            stmt2_has_negation = any(neg in word_tokenize(stmt2["text"].lower()) for neg in neg_words)
            
            if stmt1_has_negation != stmt2_has_negation:
                contradictions.append({
                    "statement1": stmt1,
                    "statement2": stmt2,
                    "similarity": similarity,
                    "contradiction_type": "negation"
                })
        
        return contradictions
    
    def detect_inconsistencies(self, transcriptions: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Detect inconsistencies between different interviews.
        
        Args:
            transcriptions: Dictionary mapping interview IDs to transcripts
            
        Returns:
            Dictionary with inconsistency analysis results
        """
        logger.info("Detecting inconsistencies across interviews")
        
        if len(transcriptions) < 2:
            logger.warning("Need at least 2 interviews to detect inconsistencies")
            return {"error": "Need at least 2 interviews to detect inconsistencies"}
        
        # Extract statements by speaker for each interview
        all_statements_by_speaker = {}
        for interview_id, transcript in transcriptions.items():
            statements_by_speaker = self._extract_statements_by_speaker(transcript)
            
            for speaker, statements in statements_by_speaker.items():
                if speaker not in all_statements_by_speaker:
                    all_statements_by_speaker[speaker] = {}
                
                all_statements_by_speaker[speaker][interview_id] = statements
        
        # Find inconsistencies between interviews for each speaker
        inconsistencies = []
        
        for speaker, interviews in all_statements_by_speaker.items():
            if len(interviews) < 2:
                continue  # Skip speakers who appear in only one interview
            
            # Compare statements across different interviews
            interview_ids = list(interviews.keys())
            for i in range(len(interview_ids)):
                for j in range(i + 1, len(interview_ids)):
                    id1, id2 = interview_ids[i], interview_ids[j]
                    
                    # Combine statements from both interviews
                    combined_statements = interviews[id1] + interviews[id2]
                    
                    # Find similar statements
                    similar_pairs = self._find_similar_statements(combined_statements)
                    
                    # Process similar pairs
                    for idx1, idx2, sim_score in similar_pairs:
                        # Check if statements are from different interviews
                        stmt1 = combined_statements[idx1]
                        stmt2 = combined_statements[idx2]
                        
                        # Only consider pairs from different interviews
                        if (idx1 < len(interviews[id1]) and idx2 >= len(interviews[id1])) or \
                           (idx2 < len(interviews[id1]) and idx1 >= len(interviews[id1])):
                            
                            # Ensure stmt1 is from id1 and stmt2 is from id2
                            if idx1 >= len(interviews[id1]):
                                stmt1, stmt2 = stmt2, stmt1
                            
                            # Add source information
                            stmt1["interview_id"] = id1
                            stmt2["interview_id"] = id2
                            
                            # Check for potential contradictions
                            similar_statement_pair = (stmt1, stmt2, sim_score)
                            contradictions = self._detect_contradictions([similar_statement_pair])
                            
                            if contradictions:
                                for contradiction in contradictions:
                                    inconsistencies.append({
                                        "speaker": speaker,
                                        "interview1": id1,
                                        "interview2": id2,
                                        "statement1": contradiction["statement1"],
                                        "statement2": contradiction["statement2"],
                                        "similarity": sim_score,
                                        "contradiction_type": contradiction["contradiction_type"]
                                    })
                            else:
                                # If no contradiction detected, still record as a similar statement
                                inconsistencies.append({
                                    "speaker": speaker,
                                    "interview1": id1,
                                    "interview2": id2,
                                    "statement1": stmt1,
                                    "statement2": stmt2,
                                    "similarity": sim_score,
                                    "contradiction_type": "similar_statement"
                                })
        
        logger.info(f"Found {len(inconsistencies)} potential inconsistencies")
        
        # Group inconsistencies by type
        contradictions = [inc for inc in inconsistencies if inc["contradiction_type"] == "negation"]
        similar_statements = [inc for inc in inconsistencies if inc["contradiction_type"] == "similar_statement"]
        
        return {
            "total_inconsistencies": len(inconsistencies),
            "contradictions": contradictions,
            "similar_statements": similar_statements
        }