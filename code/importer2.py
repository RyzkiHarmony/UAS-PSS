import os
import sys
import csv
import json
from random import randint
import time

# Django setup
sys.path.append(os.path.abspath(os.path.join(__file__, *[os.pardir] * 3)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'simplelms.settings'
import django

django.setup()

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from lms_core.models import Course, CourseMember, CourseContent, Comment

start_time = time.time()
filepath = './csv_data/'

# Import Users
with open(filepath + 'user-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    obj_create = []
    for row in reader:
        if not User.objects.filter(username=row['username']).exists():
            obj_create.append(User(
                username=row['username'],
                password=make_password(row['password']),
                email=row['email'],
                first_name=row['firstname'],
                last_name=row['lastname']
            ))
    User.objects.bulk_create(obj_create)

# Import Courses
with open(filepath + 'course-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    obj_create = []
    for row in reader:
        if not Course.objects.filter(name=row['name']).exists():
            obj_create.append(Course(
                name=row['name'],
                price=row['price'],
                description=row['description'],
                teacher=User.objects.get(pk=int(row['teacher']))
            ))
    Course.objects.bulk_create(obj_create)

# Import Course Members
with open(filepath + 'member-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    obj_create = []
    for row in reader:
        if not CourseMember.objects.filter(course_id=int(row['course_id']), user_id=int(row['user_id'])).exists():
            obj_create.append(CourseMember(
                course_id=Course.objects.get(pk=int(row['course_id'])),
                user_id=User.objects.get(pk=int(row['user_id'])),
                roles=row['roles']
            ))
    CourseMember.objects.bulk_create(obj_create)

# Import Course Content
with open(filepath + 'contents.json') as jsonfile:
    contents = json.load(jsonfile)
    obj_create = []
    for row in contents:
        if not CourseContent.objects.filter(name=row['name']).exists():
            obj_create.append(CourseContent(
                course_id=Course.objects.get(pk=int(row['course_id'])),
                video_url=row['video_url'],
                name=row['name'],
                description=row['description']
            ))
    CourseContent.objects.bulk_create(obj_create)

# Import Comments
with open(filepath + 'comments.json') as jsonfile:
    comments = json.load(jsonfile)
    obj_create = []
    with open('missing_course_members.log', 'w') as log_file:  # Log missing course members
        for row in comments:
            if int(row['user_id']) > 50:
                row['user_id'] = randint(5, 40)

            user = User.objects.get(pk=int(row['user_id']))
            course_content = CourseContent.objects.get(pk=int(row['content_id']))
            course_member = CourseMember.objects.filter(user_id=user, course_id=course_content.course_id).first()

            if not course_member:
                log_file.write(f"user_id={row['user_id']}, course_id={course_content.course_id}\n")
                continue

            if not Comment.objects.filter(content_id=course_content, member_id=course_member).exists():
                obj_create.append(Comment(
                    content_id=course_content,
                    member_id=course_member,
                    comment=row['comment']
                ))
    Comment.objects.bulk_create(obj_create)

print("--- %s seconds ---" % (time.time() - start_time))