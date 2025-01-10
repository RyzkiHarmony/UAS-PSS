from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from lms_core.models import Course, User, Profile, CourseMember
from django.core import serializers
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import json





def index(request):
    return HttpResponse("<h1>Hello World</h1>")
    
def testing(request):
    dataCourse = Course.objects.all()
    dataCourse = serializers.serialize("python", dataCourse)
    return JsonResponse(dataCourse, safe=False)

def addData(request): # jangan lupa menambahkan fungsi ini di urls.py
    course = Course(
        name = "Belajar Django",
        description = "Belajar Django dengan Mudah",
        price = 1000000,
        teacher = User.objects.get(username="admin")
    )
    course.save()
    return JsonResponse({"message": "Data berhasil ditambahkan"})

def editData(request):
    course = Course.objects.filter(name="Belajar Django").first()
    course.name = "Belajar Django Setelah update"
    course.save()
    return JsonResponse({"message": "Data berhasil diubah"})

def deleteData(request):
    course = Course.objects.filter(name__icontains="Belajar Django").first()
    course.delete()
    return JsonResponse({"message": "Data berhasil dihapus"})


@csrf_exempt
def register_user(request):
    if request.method == 'POST':
        # Parsing JSON data
        data = json.loads(request.body)
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        phone_number = data.get('phone_number', '')  # optional
        description = data.get('description', '')  # optional
        profile_picture = data.get('profile_picture', None)  # optional, assume base64 encoded

        try:
            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name.split()[0],  # ambil nama depan sebagai first_name
                last_name=" ".join(full_name.split()[1:]),  # ambil sisa nama sebagai last_name
            )

            # Create profile for the user
            profile = Profile.objects.create(
                user=user,
                phone_number=phone_number,
                description=description,
                profile_picture=profile_picture
            )

            return JsonResponse({"message": "Registrasi berhasil!"}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Gunakan POST untuk mendaftar."}, status=400)

def show_profile(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        joined_courses = CourseMember.objects.filter(user_id=user).values('course_id__name', 'course_id__description')
        created_courses = Course.objects.filter(teacher=user).values('name', 'description')
        user_data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "joined_courses": list(joined_courses),  
            "created_courses": list(created_courses)  
        }
        return JsonResponse({"user_profile": user_data}, status=200)
    except User.DoesNotExist:
        return JsonResponse({"error": "User tidak ditemukan."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def edit_profile(request):
    if request.method == 'POST':
        try:
            # Ambil Authorization header
            auth_header = request.headers.get('Authorization')

            if auth_header:
                # Parse body JSON
                data = json.loads(request.body)
                
                # Ambil data dari request
                first_name = data.get('first_name')
                last_name = data.get('last_name')
                email = data.get('email')
                phone_number = data.get('phone_number')
                description = data.get('description')
                profile_picture = data.get('profile_picture')

                # Ambil user yang lagi login dari session
                user = User.objects.filter(first_name=first_name).first()  
                profile, created = Profile.objects.get_or_create(user=user)


                # Update data user
                if user:
                    user.first_name = first_name
                    user.last_name = last_name
                    user.email = email
                    user.save()  # Simpan perubahan
                    profile.phone_number = phone_number
                    profile.description = description
                    profile.profile_picture = profile_picture
                    profile.save()  # Simpan perubahan profil

                    return JsonResponse({"message": "Update berhasil!"}, status=200)
                else:
                    return JsonResponse({"error": "User not found"}, status=404)
            else:
                # Kalau Authorization nggak ada
                return JsonResponse({'error': 'Authorization header missing'}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
