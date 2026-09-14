from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "role"]
        extra_kwargs = {
            "password": {"write_only": True},
            # role/staff/superuser flags are never client-settable via self-registration
            # or self-edit - only the Django admin or a trusted internal flow may grant them.
            "role": {"read_only": True},
        }

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ResponseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "is_superuser"]