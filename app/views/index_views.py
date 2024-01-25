from django.shortcuts import render, redirect, HttpResponseRedirect


def index_view(request):
    return render(request, "basic/index.html")
