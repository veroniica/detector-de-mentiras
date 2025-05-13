import logging
import json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def format_as_script(result):
    """
    Format the transcription result as a script with timestamps.

    Args:
        result (dict): Transcription result

    Returns:
        str: Formatted script
    """
    try:
        logger.info(f"Formatting transcription result as script: {json.dumps(result)}")
        transcript = result.get("results", {})
        items = transcript.get("items", [])
        speaker_labels = transcript.get("speaker_labels", {})
        segments = speaker_labels.get("segments", [])

        # Create a mapping of item IDs to speaker labels
        speaker_mapping = {}
        for segment in segments:
            speaker_label = segment.get("speaker_label", "Unknown")
            for item in segment.get("items", []):
                speaker_mapping[item.get("start_time")] = speaker_label

        # Format the transcript as a script
        script_lines = []
        current_speaker = None
        current_line = ""
        current_start_time = None

        for item in items:
            # Skip non-pronunciation items (like punctuation)
            if item.get("type") != "pronunciation":
                continue

            start_time = item.get("start_time")
            end_time = item.get("end_time")
            content = item.get("alternatives", [{}])[0].get("content", "")
            speaker = speaker_mapping.get(start_time, "Unknown")

            # Format timestamp as MM:SS
            timestamp = format_timestamp(float(start_time))

            # If speaker changes or significant time gap, start a new line
            if speaker != current_speaker or current_line == "":
                if current_line:
                    script_lines.append(
                        f"[{format_timestamp(float(current_start_time))}] {current_speaker}: {current_line}"
                    )
                current_speaker = speaker
                current_line = content
                current_start_time = start_time
            else:
                current_line += " " + content

        # Add the last line
        if current_line:
            script_lines.append(
                f"[{format_timestamp(float(current_start_time))}]{current_speaker}: {current_line}"
            )

        return "\n".join(script_lines)

    except Exception as e:
        logger.error(f"Error formatting script: {str(e)}")
        raise


def format_timestamp(seconds):
    """
    Format seconds as MM:SS.

    Args:
        seconds (float): Time in seconds

    Returns:
        str: Formatted timestamp
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"
