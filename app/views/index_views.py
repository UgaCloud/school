from django.shortcuts import render, redirect, HttpResponseRedirect

from app.models.classes import Class


def index_view(request):
    
    return render(request, "index.html")
