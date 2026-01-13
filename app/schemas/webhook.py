import uuid

from pydantic import BaseModel, HttpUrl


class WebhookAudioRequest(BaseModel):
    meeting_id: uuid.UUID
    file_url: HttpUrl
