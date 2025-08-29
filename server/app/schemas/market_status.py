from typing import Optional
from pydantic import BaseModel, Field


class MarketStatusResponse(BaseModel):
    """Market status response model"""
    
    is_live: bool = Field(
        ..., 
        description="Whether the overnight options trading session is currently active"
    )
    active_time_range: str = Field(
        ..., 
        description="The active trading time range in Eastern Time",
        example="3:00 PM - 4:00 PM ET"
    )
    current_time_et: str = Field(
        ..., 
        description="Current time in Eastern Time format",
        example="3:25 PM ET"
    )
    session_start_utc: str = Field(
        ..., 
        description="Today's session start time in UTC ISO format",
        example="2024-08-27T19:20:00Z"
    )
    session_end_utc: str = Field(
        ..., 
        description="Today's session end time in UTC ISO format",
        example="2024-08-27T19:40:00Z"
    )
    next_active_session: Optional[str] = Field(
        None, 
        description="Next active session start time in UTC ISO format (null if currently active)",
        example="2024-08-28T19:20:00Z"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_live": False,
                "active_time_range": "3:00 PM - 4:00 PM ET",
                "current_time_et": "2:15 PM ET",
                "session_start_utc": "2024-08-27T19:20:00Z",
                "session_end_utc": "2024-08-27T19:40:00Z",
                "next_active_session": "2024-08-27T19:20:00Z"
            }
        }