from ninja import NinjaAPI, UploadedFile, File, Form
from ninja.responses import Response
from lms_core.schema import CourseSchemaOut, CourseMemberOut, CourseSchemaIn, AnnouncementCreateSchema, AnnouncementEditSchema, AnnouncementResponseSchema
from lms_core.schema import CourseContentMini, CourseContentFull, CompletionTrackingCreateSchema, BookmarkRequestSchema, CourseContentUpdateSchema
from lms_core.schema import CourseCommentOut, CourseCommentIn, CompletionTrackingResponseSchema, BookmarkResponseSchema, PublishContentSchema, GetCourseContentSchema
from lms_core.models import Course, CourseMember, CourseContent, Comment, Profile, Announcement, CompletionTracking, Bookmark
from django.forms.models import model_to_dict
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from ninja.pagination import paginate, PageNumberPagination

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
import json



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

@apiv1.post("/edit-profile/", auth=apiAuth)
def edit_profile(request):
    try:
        data = json.loads(request.body)

        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        description = data.get('description')
        profile_picture = data.get('profile_picture')

        user = User.objects.filter(email=email).first()
        
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        user.first_name = first_name
        user.last_name = last_name
        user.save()

        profile, created = Profile.objects.get_or_create(user=user)
        profile.phone_number = phone_number
        profile.description = description

        if profile_picture:
            profile.profile_picture = profile_picture
        profile.save()
        
        user_data = model_to_dict(user)
        profile_data = model_to_dict(profile)

        if profile.profile_picture:
            profile_data['profile_picture'] = profile.profile_picture.url

        return JsonResponse({
            "user": user_data,
            "profile": profile_data,
            "message": "Profile updated successfully!"
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@apiv1.post("/announcements/", auth=apiAuth, response=AnnouncementResponseSchema)
def create_announcement(request, data: AnnouncementCreateSchema):
    created_by_username = data.created_by

    try:
        created_by_user = User.objects.get(username=created_by_username)
    except User.DoesNotExist:
        return JsonResponse({"detail": "User not found"}, status=404)

    if not created_by_user.is_staff:
        return JsonResponse({"detail": "Only teachers can create announcements"}, status=403)

    course = get_object_or_404(Course, id=data.course_id)

    announcement = Announcement.objects.create(
        course=course,
        teacher=created_by_user,  created_by=created_by_user,  title=data.title,
        content=data.content,
        show_date=data.show_date,
    )

    return JsonResponse({
        "id": announcement.id,
        "course_id": announcement.course.id,
        "teacher_id": announcement.teacher.id,
        "created_by": announcement.created_by.username,  "title": announcement.title,
        "content": announcement.content,
        "show_date": announcement.show_date,
        "date_posted": announcement.date_posted,
    }, status=201)
    
@apiv1.get("/show-announcement/", auth=apiAuth, response=AnnouncementResponseSchema)
def show_announcement(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    
    announcements = Announcement.objects.filter(course=course)
    
    announcement_data = []
    for announcement in announcements:
        announcement_data.append({
            "id": announcement.id,
            "course_id": announcement.course.id,
            "teacher_id": announcement.teacher.id,
            "created_by": announcement.created_by.username,
            "title": announcement.title,
            "content": announcement.content,
            "show_date": announcement.show_date,
            "date_posted": announcement.date_posted,
        })

    return JsonResponse({
        "course_id": course.id,
        "announcements": announcement_data
    }, status=200)

@apiv1.put("/edit-announcement/{announcement_id}", auth=apiAuth)
def edit_announcement(request, announcement_id: int, data: AnnouncementEditSchema):
    announcement = get_object_or_404(Announcement, id=announcement_id)

    if request.user.id != announcement.teacher.id or not request.user.is_staff:
        return JsonResponse({"detail": "Only the teacher who created this announcement can edit it."}, status=403)

    announcement.title = data.title
    announcement.content = data.content
    announcement.show_date = data.show_date
    announcement.save()

    return JsonResponse({
        "message": "Announcement updated successfully",
        "announcement": {
            "id": announcement.id,
            "course_id": announcement.course.id,
            "teacher_id": announcement.teacher.id,
            "title": announcement.title,
            "content": announcement.content,
            "show_date": announcement.show_date,
            "date_posted": announcement.date_posted,
        }
    }, status=200)
    
    
@apiv1.delete("/delete-announcement/{announcement_id}", auth=apiAuth)
def delete_announcement(request, announcement_id: int):
    announcement = get_object_or_404(Announcement, id=announcement_id)

    if request.user.id != announcement.teacher.id or not request.user.is_staff:
        return JsonResponse({"detail": "Only the teacher who created this announcement can delete it."}, status=403)

    announcement.delete()

    return JsonResponse({
        "message": "Announcement deleted successfully",
        "announcement_id": announcement_id
    }, status=200)

@apiv1.post("/add-completion/", auth=apiAuth)
def add_completion_tracking(request, data: CompletionTrackingCreateSchema):
    student_username = data.student_username  
    try:
        student = User.objects.get(username=student_username)
    except User.DoesNotExist:
        return JsonResponse({"detail": "User not found"}, status=404)

    content = get_object_or_404(CourseContent, id=data.content_id)

    completion, created = CompletionTracking.objects.update_or_create(
        student=student,
        content=content,
        defaults={'completed': True, 'completed_at': timezone.now()}
    )

    return JsonResponse({
        "student_username": student.username,
        "content_id": content.id,
        "completed": completion.completed,
        "completed_at": completion.completed_at,
    }, status=200)

@apiv1.get("/show-completion/", auth=apiAuth, response=CompletionTrackingResponseSchema)
def show_completion(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    course_contents = CourseContent.objects.filter(course_id=course.id)

    completions = CompletionTracking.objects.filter(content__in=course_contents)

    completion_data = []
    for completion in completions:
        completion_data.append({
            "student_id": completion.student.id,
            "student_username": completion.student.username,
            "content_id": completion.content.id,
            "content_name": completion.content.name,
            "completed": completion.completed,
            "completed_at": completion.completed_at,
        })

    return JsonResponse({
        "course_id": course.id,
        "completions": completion_data
    }, status=200)

@apiv1.delete("/delete-completion/", auth=apiAuth)
def delete_completion(request, student_id: int, content_id: int):
    student = get_object_or_404(User, id=student_id)
    
    completion = CompletionTracking.objects.filter(student=student, content_id=content_id).first()
    
    if not completion:
        return JsonResponse({"error": "Completion not found for this student and content."}, status=404)

    completion.delete()
    
    return JsonResponse({"message": "Completion successfully deleted."}, status=200)

@apiv1.post("/add-bookmark/", auth=apiAuth)
def add_bookmark(request, data: BookmarkRequestSchema):
    student_id = data.student_id
    content_id = data.content_id

    student = User.objects.get(id=student_id)  
    content = CourseContent.objects.get(id=content_id)  
    if Bookmark.objects.filter(student=student, content=content).exists():
        return JsonResponse({"error": "You have already bookmarked this content."}, status=400)
    
    Bookmark.objects.create(student=student, content=content)
    
    return JsonResponse({"message": "Bookmark successfully added."}, status=200)


@apiv1.get("/show-bookmark/", auth=apiAuth, response=BookmarkResponseSchema)
def show_bookmark(request):
    student_id = request.GET.get("student_id")

    student = User.objects.get(id=student_id)  
    bookmarks = Bookmark.objects.filter(student=student)

    bookmark_data = []
    for bookmark in bookmarks:
        content = bookmark.content
        try:
            if hasattr(content, 'course'):
                course = content.course
            else:
                course = None  
        except AttributeError:
            return JsonResponse({"error": "Content does not have a course field."}, status=400)
        
        bookmark_data.append({
            "id": bookmark.id,
            "student_id": bookmark.student.id,
            "content_id": content.id,
            "content_name": content.name,
            "course_id": course.id if course else None,  "course_name": course.name if course else "No Course"  })

    return JsonResponse({"bookmarks": bookmark_data}, status=200)


@apiv1.delete("/delete-bookmark/", auth=apiAuth)
def delete_bookmark(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    
    student_id = body.get("student_id")
    content_id = body.get("content_id")

    if not student_id or not content_id:
        return JsonResponse({"error": "Missing required fields."}, status=400)

    try:
        student = User.objects.get(id=student_id)
        content = CourseContent.objects.get(id=content_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "Student not found."}, status=404)
    except CourseContent.DoesNotExist:
        return JsonResponse({"error": "Content not found."}, status=404)

    bookmark = Bookmark.objects.filter(student=student, content=content).first()
    if not bookmark:
        return JsonResponse({"error": "Bookmark not found."}, status=404)

    bookmark.delete()

    return JsonResponse({"message": "Bookmark successfully deleted."}, status=200)

@apiv1.put("/publish-content/{content_id}/", auth=apiAuth)
def publish_content(request, content_id: int, data: PublishContentSchema):
    course_content = get_object_or_404(CourseContent, id=content_id)

    user = get_object_or_404(User, username=data.username)
    
    if user != course_content.teacher:
        return JsonResponse({"message": "You are not authorized to perform this action."}, status=403)

    course_content.is_published = data.is_published
    course_content.save()

    return JsonResponse({
        "message": "Course content publication status updated successfully",
        "is_published": course_content.is_published
    }, status=200)

@apiv1.put("/update-content/{content_id}/", auth=apiAuth)
def update_course_content(request, content_id: int, data: CourseContentUpdateSchema):
    course_content = get_object_or_404(CourseContent, id=content_id)
    
    if data.name is not None:
        course_content.name = data.name
    if data.description is not None:
        course_content.description = data.description
    if data.video_url is not None:
        course_content.video_url = data.video_url
    if data.file_attachment is not None:
        course_content.file_attachment = data.file_attachment
    if data.course_id is not None:
        course_content.course_id = get_object_or_404(Course, id=data.course_id)
    if data.parent_id is not None:
        course_content.parent_id = get_object_or_404(CourseContent, id=data.parent_id)
    if data.teacher_id is not None:
        course_content.teacher = get_object_or_404(User, id=data.teacher_id)

    course_content.save()

    return JsonResponse({
        "message": "Course content updated successfully",
        "content_id": course_content.id
    }, status=200)

@apiv1.post("/course-content/{course_id}/", auth=apiAuth)
def get_course_content(request, course_id: int, data: GetCourseContentSchema):
    username = data.username
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"message": "User not found"}, status=404)

    try:
        profile = Profile.objects.get(user=user)
        is_teacher = profile.role == 'teacher'  
    except Profile.DoesNotExist:
        is_teacher = False

    if is_teacher:
        course_contents = CourseContent.objects.filter(course_id=course_id)
    else:
        course_contents = CourseContent.objects.filter(course_id=course_id, is_published=True)

    contents_data = []
    for content in course_contents:
        contents_data.append({
            "name": content.name,
            "description": content.description,
            "video_url": content.video_url,
            "file_attachment": content.file_attachment.url if content.file_attachment else None,
            "is_published": content.is_published,
        })

    return JsonResponse({
        "message": "Course content fetched successfully",
        "contents": contents_data
    }, status=200)
