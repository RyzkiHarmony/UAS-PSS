from ninja import NinjaAPI, UploadedFile, File, Form
from ninja.responses import Response
from lms_core.schema import CourseSchemaOut, CourseMemberOut, CourseSchemaIn
from lms_core.schema import UserRegistrationSchema, UserRegistrationSchemaOut
from lms_core.schema import AnnouncementSchemaIn,AnnouncementSchemaOut
from lms_core.schema import CourseContentMini, CourseContentFull
from lms_core.schema import CourseCommentOut, CourseCommentIn
from lms_core.schema import FeedbackSchemaIn, FeedbackSchemaOut, FeedbackListSchemaOut, ShowFeedbackSchemaOut, EditFeedbackSchema
from lms_core.schema import BookmarkSchemaIn, BookmarkSchemaOut, ShowBookmarkSchemaOut
from lms_core.schema import BatchEnrollSchemaIn
from lms_core.models import Course, CourseMember, CourseContent, Comment, Announcement, Feedback, Bookmark
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from ninja.pagination import paginate, PageNumberPagination
from .utils import validate_password 
from django.contrib.auth.models import User
from django.http import JsonResponse 
from django.db.models import Count  
import logging
logger = logging.getLogger(__name__)

apiv1 = NinjaAPI()
apiv1.add_router("/auth/", mobile_auth_router)
apiAuth = HttpJwtAuth()

@apiv1.get("/hello")
def hello(request):
    return "Hello World"
 
# - paginate list_courses
@apiv1.get("/courses", response=list[CourseSchemaOut])
@paginate(PageNumberPagination, page_size=10)
def list_courses(request):
    courses = Course.objects.select_related('teacher').all()
    return courses

# - my courses
@apiv1.get("/mycourses", auth=apiAuth, response=list[CourseMemberOut])
def my_courses(request):
    logger.info(f"User in create_announcement: {request.user}, Authenticated: {request.user.is_authenticated}")
    user = User.objects.get(id=request.user.id)
    courses = CourseMember.objects.select_related('user_id', 'course_id').filter(user_id=user)
    return courses

# - create course
@apiv1.post("/courses", auth=apiAuth, response={201:CourseSchemaOut})
def create_course(request, data: Form[CourseSchemaIn], image: UploadedFile = File(None)):
    user = User.objects.get(id=request.user.id)
    course = Course(
        name=data.name,
        description=data.description,
        price=data.price,
        image=image,
        teacher=user
    )

    if image:
        course.image.save(image.name, image)

    course.save()
    return 201, course

# - update course
@apiv1.post("/courses/{course_id}", auth=apiAuth, response=CourseSchemaOut)
def update_course(request, course_id: int, data: Form[CourseSchemaIn], image: UploadedFile = File(None)):
    if request.user.id != Course.objects.get(id=course_id).teacher.id:
        message = {"error": "Anda tidak diijinkan update course ini"}
        return Response(message, status=401)
    
    course = Course.objects.get(id=course_id)
    course.name = data.name
    course.description = data.description
    course.price = data.price
    if image:
        course.image.save(image.name, image)
    course.save()
    return course

# - detail course
@apiv1.get("/courses/{course_id}", response=CourseSchemaOut)
def detail_course(request, course_id: int):
    course = Course.objects.select_related('teacher').get(id=course_id)
    return course

# - list content course
@apiv1.get("/courses/{course_id}/contents", response=list[CourseContentMini])
def list_content_course(request, course_id: int):
    contents = CourseContent.objects.filter(course_id=course_id)
    return contents

# - detail content course
@apiv1.get("/courses/{course_id}/contents/{content_id}", response=CourseContentFull)
def detail_content_course(request, course_id: int, content_id: int):
    content = CourseContent.objects.get(id=content_id)
    return content

# - batch enroll course
@apiv1.post("/courses/{course_id}/enroll-batch", auth=apiAuth, response={200: dict})  
def batch_enroll_students(request, course_id: int, data: BatchEnrollSchemaIn):  
    # Cek apakah kursus ada dan milik pengajar  
    teacher = User.objects.get(id=request.user.id)
    try:  
        course = Course.objects.get(id=course_id, teacher=teacher)  
    except Course.DoesNotExist:  
        return Response({"error": "Course not found or you do not have permission."}, status=404)  
  
    # Daftar untuk menyimpan hasil pendaftaran  
    enrolled_students = []  
    already_enrolled = []  
  
    for student_id in data.student_ids:  
        try:  
            student = User.objects.get(id=student_id)  
            # Cek apakah siswa sudah terdaftar di kursus  
            if not CourseMember.objects.filter(course_id=course, user_id=student).exists():  # Menggunakan course_id dan user_id  
                # Daftarkan siswa ke kursus  
                CourseMember.objects.create(course_id=course, user_id=student)  # Menggunakan course_id dan user_id  
                enrolled_students.append(student_id)  
            else:  
                already_enrolled.append(student_id)  
        except User.DoesNotExist:  
            return Response({"error": f"Student with ID {student_id} does not exist."}, status=404)  
  
    return {  
        "enrolled_students": enrolled_students,  
        "already_enrolled": already_enrolled,  
    }  

# - enroll course
@apiv1.post("/courses/{course_id}/enroll", auth=apiAuth, response=CourseMemberOut)
def enroll_course(request, course_id: int):
    user = User.objects.get(id=request.user.id)
    course = Course.objects.get(id=course_id)
    course_member = CourseMember(course_id=course, user_id=user, roles="std")
    course_member.save()
    # print(course_member)
    return course_member

# - list content comment
@apiv1.get("/contents/{content_id}/comments", auth=apiAuth, response=list[CourseContentMini])
def list_content_comment(request, content_id: int):
    comments = CourseContent.objects.filter(course_id=content_id)
    return comments

# - create content comment
@apiv1.post("/contents/{content_id}/comments", auth=apiAuth, response={201: CourseCommentOut})
def create_content_comment(request, content_id: int, data: CourseCommentIn):
    user = User.objects.get(id=request.user.id)
    content = CourseContent.objects.get(id=content_id)

    if not content.course_id.is_member(user):
        message =  {"error": "You are not authorized to create comment in this content"}
        return Response(message, status=401)
    
    member = CourseMember.objects.get(course_id=content.course_id, user_id=user)
    
    comment = Comment(
        content_id=content,
        member_id=member,
        comment=data.comment
    )
    comment.save()
    return 201, comment

# - delete content comment
@apiv1.delete("/comments/{comment_id}", auth=apiAuth)
def delete_comment(request, comment_id: int):
    comment = Comment.objects.get(id=comment_id)
    if comment.member_id.user_id.id != request.user.id:
        return {"error": "You are not authorized to delete this comment"}
    comment.delete()
    return {"message": "Comment deleted"}   


@apiv1.post("/register", response={201:UserRegistrationSchemaOut})  
def register(request, data: UserRegistrationSchema):  
    # Validasi password  
    if not validate_password(data.password):  
        return Response({"error": "Password must be at least 8 characters long and include uppercase letters, lowercase letters, numbers, and special characters."}, status=400)  
  
    # Cek apakah username sudah ada  
    if User.objects.filter(username=data.username).exists():  
        return Response({"error": "Username already exists."}, status=400)  
  
    # Buat pengguna baru  
    user = User(  
        username=data.username,  
        email=data.email,  
        first_name=data.first_name,  
        last_name=data.last_name  
    )  
    user.set_password(data.password)  # Mengatur password dengan metode yang aman  
    user.save()  
  
    return 201, user


@apiv1.get("/user/activity/dashboard", auth=apiAuth, response={200: dict})  
def user_activity_dashboard(request):  
    user = User.objects.get(id=request.user.id) 
  
    # Menghitung jumlah kursus yang diikuti  
    courses_joined = CourseMember.objects.filter(user_id=user).count()  # Pastikan menggunakan user_id  
  
    # Menghitung jumlah kursus yang dibuat  
    courses_created = Course.objects.filter(teacher=user).count()  
  
    # Menghitung jumlah komentar yang ditulis  
    comments_written = Comment.objects.filter(member_id__user_id=user).count()  # Menggunakan member_id untuk mengakses user  
  
    # Mengembalikan statistik dalam format JSON  
    return {  
        "courses_joined": courses_joined,  
        "courses_created": courses_created,  
        "comments_written": comments_written,
    }  

@apiv1.get("/courses/{course_id}/analytics", response={200: dict})  
def course_analytics(request, course_id: int):  
    try:  
        course = Course.objects.get(id=course_id)  
    except Course.DoesNotExist:  
        return Response({"error": "Course not found."}, status=404)  
  
    # Menghitung jumlah anggota kursus  
    members_count = CourseMember.objects.filter(course_id=course).count()  
  
    # Menghitung jumlah konten dalam kursus  
    content_count = CourseContent.objects.filter(course_id=course).count()  
  
    # Menghitung jumlah komentar untuk kursus  
    comments_count = Comment.objects.filter(content_id__course_id=course).count()  
  
    # Menghitung jumlah umpan balik untuk kursus (jika model Feedback ada)  
    feedback_count = Feedback.objects.filter(course_id=course).count()  # Pastikan model Feedback ada  
  
    # Mengembalikan statistik dalam format JSON  
    return {  
        "members_count": members_count,  
        "content_count": content_count,  
        "comments_count": comments_count,  
        "feedback_count": feedback_count,  
    }  

@apiv1.post("/courses/{course_id}/announcements", auth=apiAuth, response={201: AnnouncementSchemaOut})  
def create_announcement(request, course_id: int, data: AnnouncementSchemaIn):  
    # Cek apakah course ada  
    try:  
        course = Course.objects.get(id=course_id)  
    except Course.DoesNotExist:  
        return Response({"error": "Course not found."}, status=404)  
    
    teacher = User.objects.get(id=request.user.id)
  
    # Cek apakah pengguna yang membuat pengumuman adalah guru dari course  
    if request.user.id != course.teacher.id:  
        return Response({"error": "You are not authorized to create an announcement for this course."}, status=403)  
  
    # Buat pengumuman baru  
    announcement = Announcement(  
        course=course,  
        teacher=teacher,  
        title=data.title,  
        content=data.content,  
    )  
    announcement.save()  
  
    return 201, {  
        "id": announcement.id,  
        "course_id": announcement.course.id,  
        "teacher_id": announcement.teacher.id,  
        "title": announcement.title,  
        "content": announcement.content,  
        "date_created": announcement.date_created,  
        "date_announcement": announcement.date_announcement  
    }  

@apiv1.get("/courses/{course_id}/announcements",auth=apiAuth, response=list[AnnouncementSchemaOut])  
def show_announcements(request, course_id: int):  
    # Cek apakah course ada  
    try:  
        course = Course.objects.get(id=course_id)  
    except Course.DoesNotExist:  
        return Response({"error": "Course not found."}, status=404)  
  
    # Ambil semua pengumuman untuk course tersebut  
    announcements = Announcement.objects.filter(course=course)  
  
    # Format data untuk respons  
    response_data = [  
        {  
            "id": announcement.id,  
            "course_id": announcement.course.id,  
            "teacher_id": announcement.teacher.id,  
            "title": announcement.title,  
            "content": announcement.content,  
            "date_created": announcement.date_created,  
            "date_announcement": announcement.date_announcement  
        }  
        for announcement in announcements  
    ]  
  
    return response_data  

@apiv1.put("/announcements/{announcement_id}",auth=apiAuth, response=AnnouncementSchemaOut)  
def edit_announcement(request, announcement_id: int, data: AnnouncementSchemaIn):   
  
    # Cek apakah pengumuman ada  
    try:  
        announcement = Announcement.objects.get(id=announcement_id)  
    except Announcement.DoesNotExist:  
        return Response({"error": "Announcement not found."}, status=404)  
  
    # Cek apakah pengguna adalah teacher dari course yang bersangkutan  
    if request.user.id != announcement.teacher.id:  
        return Response({"error": "You are not authorized to edit this announcement."}, status=403)  
  
    # Perbarui pengumuman  
    announcement.title = data.title  
    announcement.content = data.content  
    announcement.save()  
  
    return {  
        "id": announcement.id,  
        "course_id": announcement.course.id,  
        "teacher_id": announcement.teacher.id,  
        "title": announcement.title,  
        "content": announcement.content,  
        "date_created": announcement.date_created,  
        "date_announcement": announcement.date_announcement  
    }  

@apiv1.delete("/announcements/{announcement_id}",auth=apiAuth, response={200: None})  
def delete_announcement(request, announcement_id: int):  

  
    # Cek apakah pengumuman ada  
    try:  
        announcement = Announcement.objects.get(id=announcement_id)  
    except Announcement.DoesNotExist:  
        return Response({"error": "Announcement not found."}, status=404)  
  
    # Cek apakah pengguna adalah teacher dari course yang bersangkutan  
    if request.user.id != announcement.teacher.id:  
        return Response({"error": "You are not authorized to delete this announcement."}, status=403)  
  
    # Hapus pengumuman  
    announcement.delete()  
    return JsonResponse({"message": "Announcement deleted successfully."}, status=200) 

@apiv1.post("/courses/{course_id}/feedback", auth=apiAuth, response={200:FeedbackSchemaOut})  
def add_feedback(request, course_id: int, data: FeedbackSchemaIn):  
    # Cek apakah course ada  
    # course = Course.objects.get(id=course_id)  
    try:  
        course = Course.objects.get(id=course_id)  
    except Course.DoesNotExist:  
        return Response({"error": "Course not found."}, status=404)  
    
    student = User.objects.get(id=request.user.id) 
    if not CourseMember.objects.filter(course_id=course, user_id=student).exists():  
        return Response({"error": "You are not authorized to provide feedback for this course."}, status=403) 
  
    # Buat umpan balik baru  
    feedback = Feedback(  
        course=course,  
        student=student,
        rating=data.rating,  
        comments=data.comments  
    )  
    feedback.save()  
    return 200,feedback

@apiv1.get("/courses/{course_id}/feedback", response=FeedbackListSchemaOut)  
def show_feedback(request, course_id: int):  
    # Cek apakah course ada  
    try:  
        course = Course.objects.get(id=course_id)  
    except Course.DoesNotExist:  
        return Response({"error": "Course not found."}, status=404)  
  
    # Ambil semua umpan balik untuk kursus tersebut  
    feedbacks = Feedback.objects.filter(course=course)  
  
    # Siapkan data untuk respons  
    feedback_list = [  
        {  
            "id": feedback.id,  
            "course_name": feedback.course.name,  # Ambil nama kursus  
            "student_name": feedback.student.username,  # Ambil nama pengguna siswa  
            "rating": feedback.rating,  
            "comments": feedback.comments,  
            "created_at": feedback.created_at  
        }  
        for feedback in feedbacks  
    ]  
  
    return {"feedbacks": feedback_list}  

@apiv1.put("/course/feedback/{feedback_id}", auth=apiAuth, response=FeedbackSchemaOut)   
def edit_feedback(request, feedback_id: int, data: EditFeedbackSchema):    
    # Cek apakah umpan balik ada    
    try:    
        feedback = Feedback.objects.get(id=feedback_id)    
    except Feedback.DoesNotExist:    
        return Response({"error": "Feedback not found."}, status=404)    
    
    # Cek apakah pengguna adalah siswa yang memberikan umpan balik ini    
    if request.user.id != feedback.student.id:    
        return Response({"error": "You are not authorized to edit this feedback."}, status=403)    
    
    # Perbarui umpan balik    
    feedback.rating = data.rating    
    feedback.comments = data.comments    
    feedback.save()    
    
    return Response({  
        "message": "Comment updated",  # Tambahkan pesan ini  
        "feedback": FeedbackSchemaOut(    
            id=feedback.id,    
            course_id=feedback.course.id,    
            student_id=feedback.student.id,    
            rating=feedback.rating,    
            comments=feedback.comments,    
            created_at=feedback.created_at    
        )  
    })  

@apiv1.delete("/course/feedback/{feedback_id}", auth=apiAuth, response={200: None})  
def delete_feedback(request, feedback_id: int):  
    # Cek apakah umpan balik ada  
    try:  
        feedback = Feedback.objects.get(id=feedback_id)  
    except Feedback.DoesNotExist:  
        return Response({"error": "Feedback not found."}, status=404)  
  
    # Cek apakah pengguna adalah siswa yang memberikan umpan balik ini  
    if request.user.id != feedback.student.id:  
        return Response({"error": "You are not authorized to delete this feedback."}, status=403)  
  
    # Hapus umpan balik  
    feedback.delete()  
  
    return JsonResponse({"message": "Feedback deleted successfully."}, status=200)   
  
@apiv1.post("/content/bookmark", auth=apiAuth, response={200:BookmarkSchemaOut})  
def add_bookmark(request, data: BookmarkSchemaIn):  

    try:    
        content = CourseContent.objects.get(id=data.content_id)    
    except CourseContent.DoesNotExist:    
        return Response({"error": "Content not found."}, status=404)  
    
    student = User.objects.get(id=request.user.id) 
  
    # Buat umpan balik baru  
    bookmark = Bookmark(  
        student=student,  
        content_id=data.content_id
    )  
    bookmark.save()   
    return BookmarkSchemaOut(  
        id=bookmark.id,  
        content_id=bookmark.content.id,  
        student=bookmark.student.id,  
        created_at=bookmark.created_at  
    ) 

@apiv1.get("/content/bookmarks", auth=apiAuth, response={200: list[BookmarkSchemaOut]})  
def show_bookmarks(request):  
    student = User.objects.get(id=request.user.id) 
  
    # Mengambil semua bookmark yang dibuat oleh pengguna  
    bookmarks = Bookmark.objects.filter(student=student).select_related('content')  
  
    # Mengembalikan daftar bookmark dengan informasi konten  
    return [  
        BookmarkSchemaOut(  
            id=bookmark.id,  
            content_id=bookmark.content.id,  
            student=bookmark.student.id,  
            created_at=bookmark.created_at  
        )  
        for bookmark in bookmarks  
    ]  

@apiv1.delete("/content/bookmark/{bookmark_id}", auth=apiAuth, response={200: None})  
def delete_bookmark(request, bookmark_id: int):  
    student = User.objects.get(id=request.user.id) 
  
    try:  
        bookmark = Bookmark.objects.get(id=bookmark_id, student=student)  # Pastikan bookmark milik pengguna  
    except Bookmark.DoesNotExist:  
        return Response({"error": "Bookmark not found."}, status=404)  
  
    # Hapus bookmark  
    bookmark.delete()  

    return JsonResponse({"message": "Bookmark deleted successfully."}, status=200)  