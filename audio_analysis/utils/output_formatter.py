"""
Utility functions for formatting and saving output files.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any

from audio_analysis import config

logger = logging.getLogger(__name__)


class OutputFormatter:
    """
    Class for formatting and saving output files.
    """
    
    def __init__(self, output_dir: str = config.DEFAULT_OUTPUT_DIR):
        """
        Initialize the output formatter.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different output types
        self.transcript_dir = os.path.join(output_dir, "transcripts")
        self.summary_dir = os.path.join(output_dir, "summaries")
        self.sentiment_dir = os.path.join(output_dir, "sentiment")
        Path(self.transcript_dir).mkdir(exist_ok=True)
        Path(self.summary_dir).mkdir(exist_ok=True)
        Path(self.sentiment_dir).mkdir(exist_ok=True)
    
    def _format_transcript_as_script(self, transcript: List[Dict[str, Any]]) -> str:
        """
        Format transcript as a script with speakers and timestamps.
        
        Args:
            transcript: List of transcript segments with speaker information
            
        Returns:
            Formatted script as string
        """
        script_lines = []
        current_speaker = None
        
        for segment in transcript:
            if "text" not in segment or not segment["text"]:
                continue
            
            speaker = segment.get("speaker", "Unknown")
            start_timestamp = segment.get("start_timestamp", "00:00")
            text = segment["text"]
            
            # Add speaker name if it changed
            if speaker != current_speaker:
                script_lines.append(f"\n[{start_timestamp}] {speaker}:")
                current_speaker = speaker
            
            # Add the text
            script_lines.append(f"    {text}")
        
        return "\n".join(script_lines)
    
    def save_transcript(self, file_id: str, transcript: List[Dict[str, Any]]) -> str:
        """
        Save transcript as both script format and JSON.
        
        Args:
            file_id: Identifier for the audio file
            transcript: List of transcript segments with speaker information
            
        Returns:
            Path to the saved script file
        """
        logger.info(f"Saving transcript for {file_id}")
        
        # Save as script format
        script_path = os.path.join(self.transcript_dir, f"{file_id}_script.txt")
        script_content = self._format_transcript_as_script(transcript)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Save as JSON for programmatic access
        json_path = os.path.join(self.transcript_dir, f"{file_id}_transcript.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Transcript saved to {script_path} and {json_path}")
        return script_path
    
    def save_summary(self, file_id: str, summary: Dict[str, Any]) -> str:
        """
        Save summary and main ideas.
        
        Args:
            file_id: Identifier for the audio file
            summary: Dictionary with summary and main ideas
            
        Returns:
            Path to the saved summary file
        """
        logger.info(f"Saving summary for {file_id}")
        
        # Format summary as text
        summary_text = f"# Summary for {file_id}\n\n"
        summary_text += "## Summary\n\n"
        summary_text += f"{summary.get('summary', 'No summary available.')}\n\n"
        
        summary_text += "## Main Ideas\n\n"
        for i, idea in enumerate(summary.get('main_ideas', []), 1):
            summary_text += f"{i}. {idea}\n"
        
        # Save as text file
        summary_path = os.path.join(self.summary_dir, f"{file_id}_summary.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        
        # Save as JSON for programmatic access
        json_path = os.path.join(self.summary_dir, f"{file_id}_summary.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Summary saved to {summary_path} and {json_path}")
        return summary_path
    
    def save_sentiment_analysis(self, file_id: str, sentiment_analysis: List[Dict[str, Any]]) -> str:
        """
        Save sentiment and deception analysis.
        
        Args:
            file_id: Identifier for the audio file
            sentiment_analysis: List of segments with sentiment and deception analysis
            
        Returns:
            Path to the saved sentiment analysis file
        """
        logger.info(f"Saving sentiment analysis for {file_id}")
        
        # Format sentiment analysis as text
        text = f"# Sentiment and Deception Analysis for {file_id}\n\n"
        
        # Calculate overall statistics
        deception_scores = [s["deception"]["deception_score"] for s in sentiment_analysis 
                           if "deception" in s and "deception_score" in s["deception"]]
        
        if deception_scores:
            avg_deception = sum(deception_scores) / len(deception_scores)
            max_deception = max(deception_scores)
            text += f"## Overall Analysis\n\n"
            text += f"Average deception score: {avg_deception:.2f}\n"
            text += f"Maximum deception score: {max_deception:.2f}\n\n"
            
            if avg_deception > 0.6:
                text += "⚠️ **High likelihood of deception detected**\n\n"
            elif avg_deception > 0.4:
                text += "⚠️ **Moderate likelihood of deception detected**\n\n"
            else:
                text += "✓ **Low likelihood of deception detected**\n\n"
        
        text += "## Segment Analysis\n\n"
        
        # Add segment-by-segment analysis
        for i, segment in enumerate(sentiment_analysis, 1):
            if "segment" not in segment:
                continue
                
            seg_text = segment["segment"].get("text", "")
            speaker = segment["segment"].get("speaker", "Unknown")
            timestamp = segment["segment"].get("start_timestamp", "00:00")
            
            text += f"### Segment {i} - [{timestamp}] {speaker}\n\n"
            text += f'"{seg_text}"\n\n'
            
            # Add sentiment information
            if "sentiment" in segment:
                sentiment = segment["sentiment"]
                compound = sentiment.get("compound", 0)
                
                text += "**Sentiment:**\n"
                if compound > 0.2:
                    text += "- Positive\n"
                elif compound < -0.2:
                    text += "- Negative\n"
                else:
                    text += "- Neutral\n"
                
                text += f"- Compound score: {compound:.2f}\n"
                text += f"- Subjectivity: {sentiment.get('subjectivity', 0):.2f}\n\n"
            
            # Add emotion information
            if "emotion" in segment and "emotions" in segment["emotion"]:
                emotions = segment["emotion"]["emotions"]
                if emotions:
                    text += "**Detected emotions:**\n"
                    for emotion in emotions[:3]:  # Top 3 emotions
                        text += f"- {emotion['label']}: {emotion['score']:.2f}\n"
                    text += "\n"
            
            # Add deception analysis
            if "deception" in segment:
                deception = segment["deception"]
                score = deception.get("deception_score", 0)
                confidence = deception.get("confidence", 0)
                
                text += "**Deception indicators:**\n"
                text += f"- Deception score: {score:.2f}\n"
                text += f"- Confidence: {confidence:.2f}\n"
                
                if "indicators" in deception:
                    indicators = deception["indicators"]
                    for indicator, value in indicators.items():
                        if value:
                            text += f"- {indicator.replace('_', ' ').title()}\n"
                
                text += "\n"
            
            text += "---\n\n"
        
        # Save as text file
        sentiment_path = os.path.join(self.sentiment_dir, f"{file_id}_sentiment.txt")
        with open(sentiment_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Save as JSON for programmatic access
        json_path = os.path.join(self.sentiment_dir, f"{file_id}_sentiment.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sentiment_analysis, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Sentiment analysis saved to {sentiment_path} and {json_path}")
        return sentiment_path
    
    def save_inconsistencies(self, inconsistencies: Dict[str, Any]) -> str:
        """
        Save inconsistency analysis across interviews.
        
        Args:
            inconsistencies: Dictionary with inconsistency analysis results
            
        Returns:
            Path to the saved inconsistency analysis file
        """
        logger.info("Saving inconsistency analysis")
        
        # Format inconsistency analysis as text
        text = "# Inconsistency Analysis Across Interviews\n\n"
        
        total = inconsistencies.get("total_inconsistencies", 0)
        text += f"Total potential inconsistencies found: {total}\n\n"
        
        # Add contradictions
        contradictions = inconsistencies.get("contradictions", [])
        text += f"## Contradictions ({len(contradictions)})\n\n"
        
        if contradictions:
            for i, contradiction in enumerate(contradictions, 1):
                speaker = contradiction.get("speaker", "Unknown")
                interview1 = contradiction.get("interview1", "Unknown")
                interview2 = contradiction.get("interview2", "Unknown")
                
                stmt1 = contradiction.get("statement1", {})
                stmt2 = contradiction.get("statement2", {})
                
                text += f"### Contradiction {i}\n\n"
                text += f"**Speaker:** {speaker}\n"
                text += f"**Interviews:** {interview1} vs {interview2}\n\n"
                
                text += f"**Statement in {interview1}** [{stmt1.get('start_timestamp', '00:00')}]:\n"
                text += f'"{stmt1.get("text", "")}"\n\n'
                
                text += f"**Statement in {interview2}** [{stmt2.get('start_timestamp', '00:00')}]:\n"
                text += f'"{stmt2.get("text", "")}"\n\n'
                
                text += f"**Similarity score:** {contradiction.get('similarity', 0):.2f}\n\n"
                text += "---\n\n"
        else:
            text += "No direct contradictions found.\n\n"
        
        # Add similar statements
        similar_statements = inconsistencies.get("similar_statements", [])
        text += f"## Similar Statements Across Interviews ({len(similar_statements)})\n\n"
        
        if similar_statements:
            for i, similar in enumerate(similar_statements, 1):
                speaker = similar.get("speaker", "Unknown")
                interview1 = similar.get("interview1", "Unknown")
                interview2 = similar.get("interview2", "Unknown")
                
                stmt1 = similar.get("statement1", {})
                stmt2 = similar.get("statement2", {})
                
                text += f"### Similar Statement {i}\n\n"
                text += f"**Speaker:** {speaker}\n"
                text += f"**Interviews:** {interview1} vs {interview2}\n\n"
                
                text += f"**Statement in {interview1}** [{stmt1.get('start_timestamp', '00:00')}]:\n"
                text += f'"{stmt1.get("text", "")}"\n\n'
                
                text += f"**Statement in {interview2}** [{stmt2.get('start_timestamp', '00:00')}]:\n"
                text += f'"{stmt2.get("text", "")}"\n\n'
                
                text += f"**Similarity score:** {similar.get('similarity', 0):.2f}\n\n"
                text += "---\n\n"
        else:
            text += "No similar statements found across interviews.\n\n"
        
        # Save as text file
        inconsistency_path = os.path.join(self.output_dir, "inconsistency_analysis.txt")
        with open(inconsistency_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Save as JSON for programmatic access
        json_path = os.path.join(self.output_dir, "inconsistency_analysis.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(inconsistencies, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Inconsistency analysis saved to {inconsistency_path} and {json_path}")
        return inconsistency_path