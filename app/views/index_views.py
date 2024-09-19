from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from app.models.classes import Class

@login_required
def index_view(request):
    
    return render(request, "index.html")
