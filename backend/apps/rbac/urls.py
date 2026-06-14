from rest_framework.routers import DefaultRouter
from .views import PermissionViewSet, RoleViewSet, AdminUserViewSet

router = DefaultRouter()
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'users', AdminUserViewSet, basename='admin-user')

urlpatterns = router.urls
