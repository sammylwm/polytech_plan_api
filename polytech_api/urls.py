from django.contrib import admin
from django.urls import path
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView, SwaggerView
from dmr.routing import Router

from . import views

router = Router(
    "api/",
    [
        path(
            "schedule/",
            views.ScheduleController.as_view(),
            name="schedule",
        )
    ],
)

schema = build_schema(router)

urlpatterns = [
    router.to_urlpatterns(),
    path("admin/", admin.site.urls),
    path("docs/openapi.json/", OpenAPIJsonView.as_view(schema), name="openapi"),
    path("docs/swagger/", SwaggerView.as_view(schema), name="swagger"),
]
