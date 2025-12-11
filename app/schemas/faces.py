from pydantic import BaseModel


class EnrollFaceResponse(BaseModel):
    status: str
    employee_id: int
    face_id: int
