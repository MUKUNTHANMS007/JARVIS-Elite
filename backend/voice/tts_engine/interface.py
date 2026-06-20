from abc import ABC, abstractmethod
from typing import AsyncGenerator

class TTSProvider(ABC):
    """
    Unified Interface for J.A.R.V.I.S. Text-to-Speech engines.
    Enables hot-swapping between local ONNX and cloud synthesizers.
    """

    @abstractmethod
    async def generate_speech(self, text: str, voice: str, speed: float) -> bytes:
        """
        Synthesize text to complete audio bytes.
        Returns WAV or MP3 encoded audio payload.
        """
        pass

    @abstractmethod
    async def stream_speech(self, text: str, voice: str, speed: float) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text and stream chunks of audio bytes.
        Yields chunks of audio bytes as they become available.
        """
        pass

    @abstractmethod
    def get_supported_voices(self) -> list[str]:
        """
        Return a list of voice identifiers supported by this provider.
        """
        pass
