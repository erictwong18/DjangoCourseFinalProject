from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission, Lesson
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    print("SUBMIT FUNCTION")
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    print("ENDPOINT")
    print(user)
    print("ENDPOINT2")
    if str(user) is "AnonymousUser":
        print("IF IS TRUE")
        return HttpResponseRedirect(reverse(viewname='onlinecourse:login'))
    myenrollment = Enrollment.objects.get(user=user, course=course)
    mysubmission = Submission.objects.create(enrollment=myenrollment)
    myanswers = extract_answers(request)
    mysubmission.choices.set(myanswers)
    print(myanswers)
    #for answer in myanswers:
        #addChoice = get_object_or_404(Choice, pk = answer)
        #mysubmission.choices.add(addChoice)
    #print("submit")
    #print(myanswers)
    mysubmission.save()
    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course.id,mysubmission.id)))


# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
    submitted_anwsers = []
    for key in request.POST:
        print("Key: " + str(key))
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_anwsers.append(Choice.objects.get(id = choice_id))
    #print("extract_answers")
    #print(submitted_answers)
    return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
def show_exam_result(request, course_id, submission_id):
    context = {}
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)
    choices = submission.choices.all()
    mylesson = get_object_or_404(Lesson, pk=1)
    for choice in choices:
        mylesson = choice.question.lesson
    print(mylesson)
    print(choices)
    total_score = 0.0
    earned_score = 0.0
    
    for question in mylesson.question_set.all():
        total_score = total_score + question.grade
    #for choice in choices:
        #total_score = total_score + choice.question.grade
    #for lesson in course.lesson_set.all():
    for question in mylesson.question_set.all():
        shouldAdd = True
        isPresent = False
        for selectchoice in choices:
            if selectchoice in question.choice_set.all() and not selectchoice.is_correct:
                shouldAdd = False
        for setquestions in question.choice_set.all():
            if setquestions in choices:
                isPresent = True
        if shouldAdd and isPresent:
            earned_score = earned_score + question.grade    
    #for choice in choices.filter(is_correct = True):
        #earned_score = earned_score + (choice.question.grade)
    print("show_exam_result")
    print(total_score)
    print(earned_score)
    if total_score is 0.0:
        total_score = 1.0
    context['course'] = course
    context['grade'] = (earned_score/total_score) * 100.0
    context['grade_int'] = int((earned_score/total_score) * 100.0)
    context['choices'] = choices
    context['mylesson'] = mylesson
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)