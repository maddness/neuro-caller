"""Audio format conversion utilities."""
import audioop
import base64
import logging

logger = logging.getLogger(__name__)


def mulaw_to_pcm16(mulaw_data: bytes) -> bytes:
    """
    Convert mulaw audio to PCM16.

    Args:
        mulaw_data: Raw mulaw audio bytes (8kHz)

    Returns:
        PCM16 audio bytes (8kHz, 16-bit)
    """
    try:
        # Convert mulaw to linear PCM
        pcm_data = audioop.ulaw2lin(mulaw_data, 2)  # 2 = 16-bit samples
        return pcm_data
    except Exception as e:
        logger.error(f"Error converting mulaw to PCM16: {e}")
        return b''


def pcm16_to_mulaw(pcm_data: bytes) -> bytes:
    """
    Convert PCM16 audio to mulaw.

    Args:
        pcm_data: Raw PCM16 audio bytes (8kHz, 16-bit)

    Returns:
        Mulaw audio bytes (8kHz, 8-bit)
    """
    try:
        # Convert linear PCM to mulaw
        mulaw_data = audioop.lin2ulaw(pcm_data, 2)  # 2 = 16-bit samples
        return mulaw_data
    except Exception as e:
        logger.error(f"Error converting PCM16 to mulaw: {e}")
        return b''


def base64_mulaw_to_base64_pcm16(mulaw_b64: str) -> str:
    """
    Convert base64 encoded mulaw to base64 encoded PCM16.

    Args:
        mulaw_b64: Base64 encoded mulaw audio

    Returns:
        Base64 encoded PCM16 audio
    """
    try:
        # Decode base64
        mulaw_data = base64.b64decode(mulaw_b64)

        # Convert mulaw to PCM16
        pcm_data = mulaw_to_pcm16(mulaw_data)

        # Encode back to base64
        pcm_b64 = base64.b64encode(pcm_data).decode('utf-8')

        return pcm_b64
    except Exception as e:
        logger.error(f"Error converting base64 mulaw to PCM16: {e}")
        return ''


def base64_pcm16_to_base64_mulaw(pcm_b64: str) -> str:
    """
    Convert base64 encoded PCM16 to base64 encoded mulaw.

    Args:
        pcm_b64: Base64 encoded PCM16 audio

    Returns:
        Base64 encoded mulaw audio
    """
    try:
        # Decode base64
        pcm_data = base64.b64decode(pcm_b64)

        # Convert PCM16 to mulaw
        mulaw_data = pcm16_to_mulaw(pcm_data)

        # Encode back to base64
        mulaw_b64 = base64.b64encode(mulaw_data).decode('utf-8')

        return mulaw_b64
    except Exception as e:
        logger.error(f"Error converting base64 PCM16 to mulaw: {e}")
        return ''


def resample_audio(audio_data: bytes, from_rate: int, to_rate: int, sample_width: int) -> bytes:
    """
    Resample audio to a different sample rate.

    Args:
        audio_data: Raw audio bytes
        from_rate: Original sample rate (Hz)
        to_rate: Target sample rate (Hz)
        sample_width: Sample width in bytes (2 for 16-bit)

    Returns:
        Resampled audio bytes
    """
    try:
        resampled_data, _ = audioop.ratecv(
            audio_data,
            sample_width,
            1,  # mono
            from_rate,
            to_rate,
            None
        )
        return resampled_data
    except Exception as e:
        logger.error(f"Error resampling audio: {e}")
        return audio_data


def pcm16_8khz_to_24khz(pcm_data: bytes) -> bytes:
    """
    Resample PCM16 from 8kHz to 24kHz for OpenAI.

    Args:
        pcm_data: PCM16 audio at 8kHz

    Returns:
        PCM16 audio at 24kHz
    """
    return resample_audio(pcm_data, 8000, 24000, 2)


def pcm16_24khz_to_8khz(pcm_data: bytes) -> bytes:
    """
    Resample PCM16 from 24kHz to 8kHz for Twilio.

    Args:
        pcm_data: PCM16 audio at 24kHz

    Returns:
        PCM16 audio at 8kHz
    """
    return resample_audio(pcm_data, 24000, 8000, 2)
