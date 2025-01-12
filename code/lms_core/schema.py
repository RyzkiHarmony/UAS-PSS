from ninja import Schema
from typing import Optional
from datetime import datetime
from pydantic import BaseModel  
from typing import List 


from django.contrib.auth.models import User

class UserOut(Schema):
    id: int
    email: str
    first_name: str
    last_name: str

class UserRegistrationSchema(Schema):
    username:str
    email:str
    first_name:str
    last_name:str
    password:str

class UserRegistrationSchemaOut(Schema):
    username:str
    email:str
    first_name:str
    last_name:str

class CourseSchemaOut(Schema):
    id: int
    name: str
    description: str
    price: int
    image : Optional[str]
    teacher: UserOut
    created_at: datetime
    updated_at: datetime

class CourseMemberOut(Schema):
    id: int 
    course_id: CourseSchemaOut
    user_id: UserOut
    roles: str
    # created_at: datetime


class CourseSchemaIn(Schema):
    name: str
    description: str
    price: int


class CourseContentMini(Schema):
    id: int
    name: str
    description: str
    course_id: CourseSchemaOut
    created_at: datetime
    updated_at: datetime


class CourseContentFull(Schema):
    id: int
    name: str
    description: str
    video_url: Optional[str]
    file_attachment: Optional[str]
    course_id: CourseSchemaOut
    created_at: datetime
    updated_at: datetime

class CourseCommentOut(Schema):
    id: int
    content_id: CourseContentMini
    member_id: CourseMemberOut
    comment: str
    created_at: datetime
    updated_at: datetime

class CourseCommentIn(Schema):
    comment: str

class AnnouncementSchemaIn(Schema):  

    title: str  
    content: str
  
class AnnouncementSchemaOut(Schema):  
    id: int  
    course_id: int  
    teacher_id: int  
    title: str  
    content: str  
    date_created: datetime  
    date_announcement: datetime 

class FeedbackSchemaIn(Schema):  
    rating: int  
    comments: str  
  
class FeedbackSchemaOut(Schema):  
    id: int  
    course_id: int  
    student_id: int  
    rating: int  
    comments: str  
    created_at: datetime 


class ShowFeedbackSchemaOut(Schema):
    id: int  
    course_name: str  
    student_name: str  
    rating: int  
    comments: str  
    created_at: datetime 
class FeedbackListSchemaOut(BaseModel):  
    feedbacks: List[ShowFeedbackSchemaOut] 

class EditFeedbackSchema(BaseModel):  
    rating: int  
    comments: str  

class BookmarkSchemaIn(BaseModel):  
    content_id: int  
  
class BookmarkSchemaOut(BaseModel):  
    id: int  
    content_id: int  
    student: int  
    created_at: datetime  
  
class ShowBookmarkSchemaOut(BaseModel):  
    id: int  
    content_title: str  
    course_name: str  
    created_at: datetime  

class BatchEnrollSchemaIn(BaseModel):  
    student_ids: List[int]  # Daftar ID siswa yang akan didaftarkan  
    course_id: int  # ID kursus  