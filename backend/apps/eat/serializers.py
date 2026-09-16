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

    def validate(self, attrs):
        category = attrs.get("category")
        restaurant = attrs.get("restaurant")
        if category and category.restaurant_id != restaurant.id:
            raise serializers.ValidationError({"category": "Kategoriya tanlangan restoranga tegishli emas."})
        if category and not category.is_active:
            raise serializers.ValidationError({"category": "Yashirilgan kategoriyaga yangi taom qo'shib bo'lmaydi."})
        return attrs


class UpdateEatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Eat
        fields = ["name", "description", "price", "image", "category"]

    def validate(self, attrs):
        category = attrs.get("category", self.instance.category)
        if category and category.restaurant_id != self.instance.restaurant_id:
            raise serializers.ValidationError({"category": "Kategoriya tanlangan restoranga tegishli emas."})
        if category and not category.is_active and category != self.instance.category:
            raise serializers.ValidationError({"category": "Yashirilgan kategoriyaga yangi taom qo'shib bo'lmaydi."})
        return attrs


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
    eats_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = ["id", "restaurant", "name", "icon", "order", "is_active", "eats_count"]


class PublicCategorySerializer(serializers.ModelSerializer):
    eats = PublicEatSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "order", "eats"]
