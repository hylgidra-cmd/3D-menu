from rest_framework import serializers
from .models import Table

class TableSerializer(serializers.ModelSerializer):
    menu_url = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = "__all__"
        extra_kwargs = {"qr_code": {"read_only": True}}

    def get_menu_url(self, obj):
        return obj.menu_url()
