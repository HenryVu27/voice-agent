from pydantic import BaseModel
from typing import Literal
from enum import Enum


class Speaker(str, Enum):
    A = "a"
    B = "b"


class Language(str, Enum):
    VI = "vi"
    RU = "ru"
    EN = "en"


# Client -> Server
class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str  # base64 encoded audio
    speaker: Speaker
    language: Language


class StartSpeakingMessage(BaseModel):
    type: Literal["start_speaking"] = "start_speaking"
    speaker: Speaker


class StopSpeakingMessage(BaseModel):
    type: Literal["stop_speaking"] = "stop_speaking"
    speaker: Speaker


# Server -> Client
class TranscriptMessage(BaseModel):
    type: Literal["transcript"] = "transcript"
    original: str
    translated: str
    speaker: Speaker


class AudioResponseMessage(BaseModel):
    type: Literal["audio_response"] = "audio_response"
    data: str  # base64 encoded audio
    language: Language


class StatusMessage(BaseModel):
    type: Literal["status"] = "status"
    latency_ms: float


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
