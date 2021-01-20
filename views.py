from django.shortcuts import render
from django.views.generic.base import View, HttpResponseRedirect, HttpResponse
from .forms import RegisterForm, NewVideoForm, CommentForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Video, Comment
import string, random
from django.core.files.storage import FileSystemStorage
import os
from wsgiref.util import FileWrapper
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from moviepy.editor import *

class VideoFileView(View):
    def get(self, request, file_name):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file = FileWrapper(open(BASE_DIR+'/'+'videos/'+file_name, 'rb'))
        response = HttpResponse(file, content_type='video/mp4')
        response['Content-Disposition'] = 'attachment; filename={}'.format(file_name)
        return response


class HomeView(View):
    template_name = 'index.html'
    def get(self, request):
        most_recent_videos = Video.objects.order_by('-id')
        print('most recent')
        print(most_recent_videos)
        return render(request, self.template_name, {'menu_active_item': 'home', 'most_recent_videos': most_recent_videos})

class LogoutView(View):
    def get(self, request):
        logout(request)
        return HttpResponseRedirect('/')

class VideoView(View):
    template_name = 'video.html'

    def get(self, request, id):
        #fetch video from DB by ID
        video_by_id = Video.objects.get(id=id)
        video_by_id.views+=1
        video_by_id.save()
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        video_by_id.path = 'http://videohostlug.ct8.pl/get_video/'+video_by_id.path
        context = {'video':video_by_id}
        

        if request.user.is_authenticated:
            comment_form = CommentForm()
            context['form'] = comment_form
            if video_by_id.likes.filter(id=request.user.id).exists():
                is_liked = True
                context['is_liked'] = is_liked
            if video_by_id.dislikes.filter(id=request.user.id).exists():
                is_disliked = True
                context['is_disliked'] = is_disliked
        
        comments = Comment.objects.filter(video__id=id).order_by('-datetime')[:20]
        context['comments'] = comments
        return render(request, self.template_name, context)




class CommentView(View):
    template_name = 'comment.html'

    def post(self, request):
        # pass filled out HTML-Form from View to CommentForm()
        form = CommentForm(request.POST)
        if form.is_valid():
            # create a Comment DB Entry
            text = form.cleaned_data['text']
            video_id = request.POST['video']
            video = Video.objects.get(id=video_id)
            
            new_comment = Comment(text=text, user=request.user, video=video)
            new_comment.save()
            return HttpResponseRedirect('/video/{}'.format(str(video_id)))
        return HttpResponse('This is Register view. POST Request.')

class RegisterView(View):
    template_name = 'register.html'
    
    def get(self, request):
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})

    def post(self, request):
        # pass filled out HTML-Form from View to RegisterForm()
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            email = form.cleaned_data.get('email')
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            new_user.save()
            login(request, new_user)
            return HttpResponseRedirect('/')
        else:
            
            return render(request, 'register.html', {'form': form})

class NewVideo(View):
    template_name = 'new_video.html'
    
    def get(self, request):
        if request.user.is_authenticated == False:
            #return HttpResponse('You have to be logged in, in order to upload a video.')
            return HttpResponseRedirect('/register')
        
        form = NewVideoForm()
        return render(request, self.template_name, {'form':form})

    def post(self, request):
        # pass filled out HTML-Form from View to NewVideoForm()
        form = NewVideoForm(request.POST, request.FILES)       
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if form.is_valid():
            title = form.cleaned_data.get('title')
            description = form.cleaned_data.get('description')
            file = form.cleaned_data.get('file')
            random_char = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            pathwithoutmp4 = random_char
            pathwithpng = pathwithoutmp4+'.png'
            path = pathwithoutmp4+'.mp4'
            fs = FileSystemStorage(location = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/videos')
            filename = fs.save(path, file)
            file_url = fs.url(filename)
            views=0
            clip = VideoFileClip(BASE_DIR+'/'+'videos/'+path)   
            thumbpath=BASE_DIR+'/public/static/'+pathwithoutmp4+'.png'
            clip.save_frame(thumbpath,t=1.50)
            new_video = Video(title=title, description=description, user=request.user, path=path, thumbpath=pathwithpng, views=views)
            new_video.save()
          
            
            # redirect to detail view template of a Video
            return HttpResponseRedirect('/video/{}'.format(new_video.id))
        else:
            return HttpResponse('Your form is not valid. Go back and try again.')



@method_decorator(login_required, name='dispatch')
class Profile(View):
    template_name = 'profile.html'
    
    def get(self, request):
        u_form = UserUpdateForm(instance=request.user)
        context = {
            'u_form': u_form         
        }
        return render(request, self.template_name, context)

    def post(self, request):
        
        u_form = UserUpdateForm(request.POST, instance=request.user)
        if u_form.is_valid():
            u_form.save()
            
            messages.success(request, f'Your account has been updated!')
            return HttpResponseRedirect('/profile')
        else:
            messages.warning(request, f'Wrong username or email')
            return HttpResponseRedirect('/profile')
    
    
def like(request, id):
    if request.user.is_authenticated:
        video = Video.objects.get(id=id)
        is_liked = False
        if video.likes.filter(id=request.user.id).exists():
            video.likes.remove(request.user)
            is_liked = False
        else:
            if video.dislikes.filter(id=request.user.id).exists():
                video.dislikes.remove(request.user)
            video.likes.add(request.user)
            is_liked = True
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    else:
        messages.warning(request, f'You have to be logged in!')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def dislike(request, id):
    if request.user.is_authenticated:
        video = Video.objects.get(id=id)
        is_disliked = False
        if video.dislikes.filter(id=request.user.id).exists():
            video.dislikes.remove(request.user)
            is_disliked = False

        else:
            if video.likes.filter(id=request.user.id).exists():
                video.likes.remove(request.user) 

            video.dislikes.add(request.user)
            is_disliked = True
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    else:
        messages.warning(request, f'You have to be logged in!')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
