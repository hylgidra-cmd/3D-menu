from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.user.serializers import ResponseUserSerializer
from .models import Restaurant, RestaurantStaff

User = get_user_model()

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
        fields = ["name", "description", "location", "coordinates", "logo", "cover_image", "primary_color"]


class PublicRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ["id", "name", "slug", "description", "location", "logo", "cover_image", "primary_color"]


class MyRestaurantSerializer(serializers.ModelSerializer):
    """Restaurant + the requesting user's own role on it (for the admin panel's restaurant switcher)."""
    role = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = ["id", "name", "slug", "logo", "primary_color", "is_active", "role"]

    def get_role(self, obj):
        request = self.context.get("request")
        staff = RestaurantStaff.objects.filter(restaurant=obj, user=request.user).first()
        return staff.role if staff else None


class RestaurantStaffSerializer(serializers.ModelSerializer):
    user = ResponseUserSerializer(read_only=True)

    class Meta:
        model = RestaurantStaff
        fields = ["id", "restaurant", "user", "role", "created_at"]


class InviteStaffSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(choices=RestaurantStaff.Role.choices, default=RestaurantStaff.Role.WAITER)

    def validate_username(self, value):
        user = User.objects.filter(username=value).first()
        if not user:
            raise serializers.ValidationError("Bunday foydalanuvchi topilmadi.")
        self._user = user
        return value

    def validate_role(self, value):
        if value == RestaurantStaff.Role.OWNER:
            raise serializers.ValidationError("Owner rolini shu yo'l bilan berib bo'lmaydi.")
        return value