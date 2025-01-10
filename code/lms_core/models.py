from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)
    role = models.CharField(max_length=10, choices=[('teacher', 'Teacher'), ('student', 'Student')], default='student')


    def __str__(self):
        return f"Profile of {self.user.username}"

class Course(models.Model):
    name = models.CharField("Nama Kursus", max_length=255)
    description = models.TextField("Deskripsi")
    price = models.IntegerField("Harga")
    image = models.ImageField("Gambar", upload_to="course", blank=True, null=True)
    teacher = models.ForeignKey(User, verbose_name="Pengajar", on_delete=models.RESTRICT)
    created_at = models.DateTimeField("Dibuat pada", auto_now_add=True)
    updated_at = models.DateTimeField("Diperbarui pada", auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Mata Kuliah"
        verbose_name_plural = "Data Mata Kuliah"
        ordering = ["-created_at"]

    def is_member(self, user):
        return CourseMember.objects.filter(course_id=self, user_id=user).exists()

ROLE_OPTIONS = [('std', "Siswa"), ('ast', "Asisten")]

class CourseMember(models.Model):
    course_id = models.ForeignKey(Course, verbose_name="matkul", on_delete=models.RESTRICT)
    user_id = models.ForeignKey(User, verbose_name="siswa", on_delete=models.RESTRICT)
    roles = models.CharField("peran", max_length=3, choices=ROLE_OPTIONS, default='std')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subscriber Matkul"
        verbose_name_plural = "Subscriber Matkul"

    def __str__(self) -> str:
        return f"{self.id} {self.course_id} : {self.user_id}"

class CourseContent(models.Model):
    name = models.CharField("judul konten", max_length=200)
    description = models.TextField("deskripsi", default='-')
    video_url = models.CharField('URL Video', max_length=200, null=True, blank=True)
    file_attachment = models.FileField("File", null=True, blank=True)
    course_id = models.ForeignKey(Course, verbose_name="matkul", on_delete=models.RESTRICT)
    parent_id = models.ForeignKey("self", verbose_name="induk", 
                                on_delete=models.RESTRICT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    teacher = models.ForeignKey(User, verbose_name="Pengajar", on_delete=models.CASCADE, null=True, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Konten Matkul"
        verbose_name_plural = "Konten Matkul"

    def __str__(self) -> str:
        return f'{self.course_id} {self.name}'


class Comment(models.Model):
    content_id = models.ForeignKey(CourseContent, verbose_name="konten", on_delete=models.CASCADE)
    member_id = models.ForeignKey(CourseMember, verbose_name="pengguna", on_delete=models.CASCADE)
    comment = models.TextField('komentar')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Komentar"
        verbose_name_plural = "Komentar"

    def __str__(self) -> str:
        return f"Komen: {self.member_id.user_id}-{self.comment}"

class Announcement(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, related_name="announcements", on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, related_name="created_announcements", on_delete=models.CASCADE, default=None, null=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    show_date = models.DateTimeField()
    date_posted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class CompletionTracking(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(CourseContent, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'content')

    def __str__(self):
        return f"{self.student.username} - {self.content.name} - Completed: {self.completed}"
    
class Bookmark(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(CourseContent, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('student', 'content')

    def __str__(self):
        return f"{self.student.username} - {self.content.name}"

