from rest_framework import serializers
from apps.user.serializers import ResponseUserSerializer
from .models import Restaurant, RestaurantStaff

class RestaurantSerializer(serializers.ModelSerializer):
    user = ResponseUserSerializer(read_only=True)
    class Meta:
        model = Restaurant
        fields = '__all__'
        # slug/is_active are not owner-editable: slug keeps public links stable,
        # is_active is reserved for platform-admin suspend/activate controls.
        extra_kwargs = {"slug": {"read_only": True}, "is_active": {"read_only": True}}


class UpdateRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ["name", "description", "location", "coordinates", "logo", "cover_image"]


class PublicRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ["id", "name", "slug", "description", "location", "logo", "cover_image"]


class MyRestaurantSerializer(serializers.ModelSerializer):
    """Restaurant + the requesting user's own role on it (for the admin panel's restaurant switcher)."""
    role = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = ["id", "name", "slug", "logo", "is_active", "role"]

    def get_role(self, obj):
        request = self.context.get("request")
        staff = RestaurantStaff.objects.filter(restaurant=obj, user=request.user).first()
        return staff.role if staff else None
