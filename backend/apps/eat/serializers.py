from rest_framework import serializers
from .models import Eat, Category


class EatSerializer(serializers.ModelSerializer):
    model_url = serializers.ReadOnlyField()
    model_url_usdz = serializers.ReadOnlyField()
    model_status = serializers.ReadOnlyField()
    model_progress = serializers.ReadOnlyField()
    model_error = serializers.ReadOnlyField()
    model_error_type = serializers.ReadOnlyField()
    usdz_status = serializers.ReadOnlyField()
    usdz_error = serializers.ReadOnlyField()
    usdz_error_type = serializers.ReadOnlyField()

    class Meta:
        model = Eat
        fields = "__all__"


class CreateEatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Eat
        fields = ["name", "description", "price", "image", "restaurant", "category"]


class PublicEatSerializer(serializers.ModelSerializer):
    model_url = serializers.ReadOnlyField()
    model_url_usdz = serializers.ReadOnlyField()
    model_status = serializers.ReadOnlyField()
    model_progress = serializers.ReadOnlyField()
    model_error = serializers.ReadOnlyField()
    model_error_type = serializers.ReadOnlyField()

    class Meta:
        model = Eat
        fields = [
            "id", "name", "description", "price", "image", "category",
            "model_url", "model_url_usdz", "model_status", "model_progress", "model_error", "model_error_type",
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class PublicCategorySerializer(serializers.ModelSerializer):
    eats = PublicEatSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "order", "eats"]
