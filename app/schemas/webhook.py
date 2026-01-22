from pydantic import BaseModel, HttpUrl


class WebhookAudioRequest(BaseModel):
    meeting_id: int
    file_url: HttpUrl
